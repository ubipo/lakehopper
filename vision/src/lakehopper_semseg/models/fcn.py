# FCN model for semantic segmentation.
# 
# Shelhamer, E., Long, J. and Darrell, T. (2016) ‘Fully Convolutional Networks for Semantic Segmentation’. arXiv. (Accessed: 10 July 2022).
# https://arxiv.org/pdf/1411.4038.pdf
# 
# Adapted from: 
# https://github.com/shelhamer/fcn.berkeleyvision.org
#  and
# https://github.com/kevinddchen/Keras-FCN/blob/main/models.py

import numpy as np
import tensorflow as tf

from .encoder import create_encoder

class BilinearInitializer(tf.keras.initializers.Initializer):
    '''Initializer for Conv2DTranspose to perform bilinear interpolation on each channel.'''
    def __call__(self, shape, dtype=None, **kwargs):
        kernel_size, _, filters, _ = shape
        arr = np.zeros((kernel_size, kernel_size, filters, filters))
        ## make filter that performs bilinear interpolation through Conv2DTranspose
        upscale_factor = (kernel_size+1)//2
        if kernel_size % 2 == 1:
            center = upscale_factor - 1
        else:
            center = upscale_factor - 0.5
        og = np.ogrid[:kernel_size, :kernel_size]
        kernel = (1-np.abs(og[0]-center)/upscale_factor) * \
                 (1-np.abs(og[1]-center)/upscale_factor) # kernel shape is (kernel_size, kernel_size)
        for i in range(filters):
            arr[..., i, i] = kernel
        return tf.convert_to_tensor(arr, dtype=dtype)


def create_fcn8(encoder_name: str, output_channels: int, shape: tuple):
    down_stack = create_encoder(encoder_name, shape)

    l2 = 1e-6

    inputs = tf.keras.layers.Input(shape=shape)

    # Downsampling through the model
    skips = down_stack(inputs)
    x = skips[-1]
    skips = list(reversed(skips[:-1]))

        # 32x
    x = tf.keras.layers.Conv2D(filters=21, kernel_size=(1,1), strides=(1,1), padding='same', activation='linear',
                            kernel_regularizer=tf.keras.regularizers.L2(l2=l2),
                            name='score7')(skips[0].output)

    # 16x
    x = tf.keras.layers.Conv2DTranspose(filters=21, kernel_size=(4,4), strides=(2,2),
                                     padding='same', use_bias=False, activation='linear',
                                     kernel_initializer=BilinearInitializer(),
                                     kernel_regularizer=tf.keras.regularizers.L2(l2=l2),
                                     name='score7_upsample')(x.output)
    y = tf.keras.layers.Conv2D(filters=21, kernel_size=(1,1), strides=(1,1), padding='same', activation='linear',
                            kernel_initializer=tf.keras.initializers.Zeros(),
                            kernel_regularizer=tf.keras.regularizers.L2(l2=l2),
                            name='score4')(skips[1].output)
    x = tf.keras.layers.Add(name='skip4')([x, y])

    # 8x
    x = tf.keras.layers.Conv2DTranspose(filters=21, kernel_size=(4,4), strides=(2,2),
                                     padding='same', use_bias=False, activation='linear',
                                     kernel_initializer=BilinearInitializer(),
                                     kernel_regularizer=tf.keras.regularizers.L2(l2=l2),
                                     name='skip4_upsample')(x.output)
    y = tf.keras.layers.Conv2D(filters=21, kernel_size=(1,1), strides=(1,1), padding='same', activation='linear',
                            kernel_initializer=tf.keras.initializers.Zeros(),
                            kernel_regularizer=tf.keras.regularizers.L2(l2=l2),
                            name='score3')(skips[2].output)
    x = tf.keras.layers.Add(name='skip3')([x, y])
    x = tf.keras.layers.Conv2DTranspose(filters=21, kernel_size=(16,16), strides=(8,8),
                                     padding='same', use_bias=False, activation='softmax',
                                     kernel_initializer=BilinearInitializer(),
                                     kernel_regularizer=tf.keras.regularizers.L2(l2=l2),
                                     name='fcn8')(x)

    last = tf.keras.layers.Conv2DTranspose(
        filters=output_channels, kernel_size=3, strides=2,
        padding='same')

    x = last(x)

    return tf.keras.Model(inputs=inputs, outputs=x)
