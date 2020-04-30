# all stuff for developing deep learning model 
import numpy as np
from keras import optimizers
from keras import layers
from keras.layers import Input, Add, Dense, Activation, ZeroPadding2D, BatchNormalization, Flatten, Conv2D, AveragePooling2D, MaxPooling2D, GlobalMaxPooling2D, Dropout
from keras.models import Model, load_model
from keras.callbacks import ModelCheckpoint, EarlyStopping, ReduceLROnPlateau
from keras.preprocessing import image
from keras.utils import layer_utils
from keras.utils.data_utils import get_file
from keras.applications.imagenet_utils import preprocess_input
from keras.utils.vis_utils import model_to_dot
from keras.utils import plot_model
from keras.initializers import glorot_uniform
import keras.backend as K
K.set_image_data_format('channels_last')
K.set_learning_phase(1)

# HDF5 file manager
import h5py

def identity_block(X, f, filters, stage, block):
    """
    Implementation of the identity block
    
    Arguments:
    X --> input tensor of shape (m, n_H_prev, n_W_prev, n_C_prev)
    f --> integer, specifying the shape of the middle CONV's window for the main path
    filters --> python list of integers, defining the number of filters in the CONV layers of the main path
    stage --> integer, used to name the layers, depending on their position in the network
    block --> string/character, used to name the layers, depending on their position in the network
    
    Returns:
    X -- output of the identity block, tensor of shape (n_H, n_W, n_C)
    """
    
    # defining name basis
    conv_name_base = 'res' + str(stage) + block + '_branch'
    bn_name_base = 'bn' + str(stage) + block + '_branch'
    
    # Retrieve Filters
    F1, F2, F3 = filters
    
    # Save the input value. will be used when in main path
    X_shortcut = X
    
    # First component of main path
    X = Conv2D(filters = F1, kernel_size = (1, 1), strides = (1,1), padding = 'valid', name = conv_name_base + '2a', kernel_initializer = "he_normal")(X)
    X = BatchNormalization(axis = 3, name = bn_name_base + '2a')(X)
    X = Activation('relu')(X)

    # Second component of main path
    X = Conv2D(filters = F2, kernel_size = (f, f), strides = (1,1), padding = 'same', name = conv_name_base + '2b', kernel_initializer = "he_normal")(X)
    X = BatchNormalization(axis = 3, name = bn_name_base + '2b')(X)
    X = Activation('relu')(X)

    # Third component of main path (≈2 lines)
    X = Conv2D(filters = F3, kernel_size = (1, 1), strides = (1,1), padding = 'valid', name = conv_name_base + '2c', kernel_initializer = "he_normal")(X)
    X = BatchNormalization(axis = 3, name = bn_name_base + '2c')(X)

    # Final step: Add shortcut value to main path, and pass it through a RELU activation (≈2 lines)
    X = Add()([X, X_shortcut])
    X = Activation('relu')(X)
    
    return X

def convolutional_block(X, f, filters, stage, block, s = 2):
    """
    Implementation of the convolutional block
    
    Arguments:
    X -- input tensor of shape (m, n_H_prev, n_W_prev, n_C_prev)
    f -- integer, specifying the shape of the middle CONV's window for the main path
    filters -- python list of integers, defining the number of filters in the CONV layers of the main path
    stage -- integer, used to name the layers, depending on their position in the network
    block -- string/character, used to name the layers, depending on their position in the network
    s -- Integer, specifying the stride to be used
    
    Returns:
    X -- output of the convolutional block, tensor of shape (n_H, n_W, n_C)
    """
    
    # defining name basis
    conv_name_base = 'res' + str(stage) + block + '_branch'
    bn_name_base = 'bn' + str(stage) + block + '_branch'
    
    # Retrieve Filters
    F1, F2, F3 = filters
    
    # Save the input value
    X_shortcut = X

    # First component of main path 
    X = Conv2D(F1, (1, 1), strides = (s,s), name = conv_name_base + '2a', kernel_initializer = "he_normal")(X)
    X = BatchNormalization(axis = 3, name = bn_name_base + '2a')(X)
    X = Activation('relu')(X)

    # Second component of main path
    X = Conv2D(filters = F2, kernel_size = (f, f), strides = (1,1), padding = 'same', name = conv_name_base + '2b', kernel_initializer = "he_normal")(X)
    X = BatchNormalization(axis = 3, name = bn_name_base + '2b')(X)
    X = Activation('relu')(X)

    # Third component of main path
    X = Conv2D(filters = F3, kernel_size = (1, 1), strides = (1,1), padding = 'valid', name = conv_name_base + '2c', kernel_initializer = "he_normal")(X)
    X = BatchNormalization(axis = 3, name = bn_name_base + '2c')(X)

    # SHORTCUT PATH
    X_shortcut = Conv2D(filters = F3, kernel_size = (1, 1), strides = (s,s), padding = 'valid', name = conv_name_base + '1',
                        kernel_initializer = 'he_normal')(X_shortcut)
    X_shortcut = BatchNormalization(axis = 3, name = bn_name_base + '1')(X_shortcut)

    # Add shortcut weight to main path
    X = Add()([X, X_shortcut])
    X = Activation('relu')(X)
    
    return X

def ResNet50(input_shape, classes, dropout_value=0):
    """
    Implementation ResNet50 the following architecture:
    CONV2D -> BATCHNORM -> RELU -> MAXPOOL -> CONVBLOCK -> IDBLOCK*2 -> CONVBLOCK -> IDBLOCK*3
    -> CONVBLOCK -> IDBLOCK*5 -> CONVBLOCK -> IDBLOCK*2 -> AVGPOOL -> TOPLAYER

    Arguments:
    input_shape -- shape of the images of the dataset
    classes -- integer, number of classes

    Returns:
    model -- a Model() instance in Keras
    """
    # Define Dropout value
    DROPOUT_VALUE = dropout_value

    # Define the input as a tensor with shape input_shape
    X_input = Input(input_shape)

    # Zero-Padding
    X = ZeroPadding2D((3, 3))(X_input)

    # Stage 1
    X = Conv2D(64, (7, 7), strides=(2, 2), name='res1', kernel_initializer="he_normal")(X)
    X = BatchNormalization(axis=3, name='bn_res1')(X)
    X = Activation('relu')(X)
    X = ZeroPadding2D((1,1))(X)
    X = MaxPooling2D((3, 3), strides=(2, 2))(X)

    # Stage 2
    X = convolutional_block(X, f=3, filters=[64, 64, 256], stage=2, block='a', s=1)
    X = Dropout(DROPOUT_VALUE)(X)
    X = identity_block(X, 3, [64, 64, 256], stage=2, block='b')
    X = Dropout(DROPOUT_VALUE)(X)
    X = identity_block(X, 3, [64, 64, 256], stage=2, block='c')
    X = Dropout(DROPOUT_VALUE)(X)

    # Stage 3 
    X = convolutional_block(X, f = 3, filters = [128, 128, 512], stage = 3, block='a', s = 2)
    X = Dropout(DROPOUT_VALUE)(X)
    X = identity_block(X, 3, [128, 128, 512], stage=3, block='b')
    X = Dropout(DROPOUT_VALUE)(X)
    X = identity_block(X, 3, [128, 128, 512], stage=3, block='c')
    X = Dropout(DROPOUT_VALUE)(X)
    X = identity_block(X, 3, [128, 128, 512], stage=3, block='d')
    X = Dropout(DROPOUT_VALUE)(X)

    # Stage 4 
    X = convolutional_block(X, f = 3, filters = [256, 256, 1024], stage = 4, block='a', s = 2)
    X = Dropout(DROPOUT_VALUE)(X)
    X = identity_block(X, 3, [256, 256, 1024], stage=4, block='b')
    X = Dropout(DROPOUT_VALUE)(X)
    X = identity_block(X, 3, [256, 256, 1024], stage=4, block='c')
    X = Dropout(DROPOUT_VALUE)(X)
    X = identity_block(X, 3, [256, 256, 1024], stage=4, block='d')
    X = Dropout(DROPOUT_VALUE)(X)
    X = identity_block(X, 3, [256, 256, 1024], stage=4, block='e')
    X = Dropout(DROPOUT_VALUE)(X)
    X = identity_block(X, 3, [256, 256, 1024], stage=4, block='f')
    X = Dropout(DROPOUT_VALUE)(X)

    # Stage 5 
    X = convolutional_block(X, f = 3, filters = [512, 512, 2048], stage = 5, block='a', s = 2)
    X = Dropout(DROPOUT_VALUE)(X)
    X = identity_block(X, 3, [512, 512, 2048], stage=5, block='b')
    X = Dropout(DROPOUT_VALUE)(X)
    X = identity_block(X, 3, [512, 512, 2048], stage=5, block='c')
    X = Dropout(DROPOUT_VALUE)(X)

    # AVGPOOL 
    X = AveragePooling2D((2,2), name="avg_pool")(X)

    # output layer
    X = Flatten()(X)
    X = Dense(classes, activation='softmax', name='fc' + str(classes))(X)
        
    # Create model
    model = Model(inputs = X_input, outputs = X, name='ResNet50')

    return model