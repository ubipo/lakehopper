# FCN model for semantic segmentation.
#
# Shelhamer, E., Long, J. and Darrell, T. (2016) ‘Fully Convolutional Networks for Semantic Segmentation’. arXiv. (Accessed: 10 July 2022).
# https://arxiv.org/pdf/1411.4038.pdf
#
# Adapted from:
# - https://github.com/shelhamer/fcn.berkeleyvision.org
# - https://github.com/kevinddchen/Keras-FCN/blob/main/models.py

import numpy as np
import tensorflow as tf
import tensorflow.keras.layers as layers

from .encoder import create_encoder
from .blocks import Conv3x3BnReLU


DECODER_FILTERS = (256, 128, 64, 32)
# DECODER_FILTERS = (256, 128, 64, 21)


class FCNBlock:
    """Block for FCN model."""

    def __init__(self, name, filters):
        self.skip_conv = Conv3x3BnReLU(filters, name=f"{name}_skip")
        self.upsample = layers.Conv2DTranspose(
            filters=filters,
            kernel_size=4,
            strides=2,
            padding="same",
            name=f"{name}_upsample",
        )
        self.add = layers.Add(name=f"{name}_add")
        self.conv = Conv3x3BnReLU(filters, name=name)

    def __call__(self, input_tensor, skip):
        x = self.upsample(input_tensor)
        y = self.skip_conv(skip)
        x = self.add([x, y])
        x = self.conv(x)
        return x


def create_fcn8(
    encoder_name: str,
    output_channels: int,
    input_shape: tuple,
    activation: str,
    encoder_trainable: bool = False,
):
    encoder, encoder_output, skips = create_encoder(
        encoder_name, input_shape, encoder_trainable
    )
    skips = list(reversed(skips))
    x = encoder_output

    # 0 blocks = fcn32, 1 block = fcn16, 2 blocks = fcn8
    x = FCNBlock("fcn_stage_1", DECODER_FILTERS[0])(x, skips[0])
    x = FCNBlock("fcn_stage_2", DECODER_FILTERS[1])(x, skips[1])
    x = FCNBlock("fcn_stage_3", DECODER_FILTERS[2])(x, skips[2])
    x = FCNBlock("fcn_stage_4", DECODER_FILTERS[3])(x, skips[3])

    x = layers.Conv2DTranspose(
        filters=21,
        kernel_size=4,
        strides=2,
        padding="same",
        activation="softmax",
        name="fcn8",
    )(x)

    # model head (define number of output classes)
    x = layers.Conv2DTranspose(
        filters=output_channels,
        kernel_size=3,
        padding="same",
        activation=activation,
        name="head_conv",
    )(x)

    return tf.keras.Model(inputs=encoder.input, outputs=x, name=f"FCN_{encoder_name}")
