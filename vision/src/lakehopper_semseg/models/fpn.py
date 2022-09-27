# FPN model for semantic segmentation
#
# Lin, T.-Y. et al. (2017) ‘Feature Pyramid Networks for Object Detection’. arXiv. (Accessed: 10 July 2022).
# http://arxiv.org/abs/1612.03144
#
# Adapted from:
# - https://github.com/qubvel/segmentation_models/blob/master/segmentation_models/models/fpn.py

import tensorflow as tf
import tensorflow.keras.layers as layers

from .encoder import create_encoder
from .blocks import Conv3x3BnReLU


def FPNBlock(pyramid_filters, name):
    def wrapper(input_tensor, skip):
        # if input tensor channels not equal to pyramid channels
        # we will not be able to sum input tensor and skip
        # so add extra conv layer to transform it
        input_filters = tf.keras.backend.int_shape(input_tensor)[3]
        if input_filters != pyramid_filters:
            input_tensor = layers.Conv2D(
                filters=pyramid_filters,
                kernel_size=(1, 1),
                kernel_initializer="he_uniform",
                name=f"{name}_pre_conv",
            )(input_tensor)

        skip = layers.Conv2D(
            filters=pyramid_filters,
            kernel_size=(1, 1),
            kernel_initializer="he_uniform",
            name=f"{name}_conv",
        )(skip)

        x = layers.UpSampling2D((2, 2), name=f"{name}_upsampling")(input_tensor)
        x = layers.Add(name=f"{name}_add")([x, skip])

        return x

    return wrapper


def DoubleConv3x3BnReLU(filters, name):
    def wrapper(input_tensor):
        x = Conv3x3BnReLU(filters, name=f"{name}a")(input_tensor)
        x = Conv3x3BnReLU(filters, name=f"{name}b")(x)
        return x

    return wrapper


def create_fpn(
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

    pyramid_filters = 256
    segmentation_filters = 128

    p5 = FPNBlock(pyramid_filters, name=f"fpn_stage_p5")(x, skips[0])
    p4 = FPNBlock(pyramid_filters, name=f"fpn_stage_p4")(p5, skips[1])
    p3 = FPNBlock(pyramid_filters, name=f"fpn_stage_p3")(p4, skips[2])
    p2 = FPNBlock(pyramid_filters, name=f"fpn_stage_p2")(p3, skips[3])

    # add segmentation head to each
    s5 = DoubleConv3x3BnReLU(segmentation_filters, name="segm_stage5")(p5)
    s4 = DoubleConv3x3BnReLU(segmentation_filters, name="segm_stage4")(p4)
    s3 = DoubleConv3x3BnReLU(segmentation_filters, name="segm_stage3")(p3)
    s2 = DoubleConv3x3BnReLU(segmentation_filters, name="segm_stage2")(p2)

    # upsampling to same resolution
    s5 = layers.UpSampling2D((8, 8), interpolation="nearest", name="upsampling_stage5")(
        s5
    )
    s4 = layers.UpSampling2D((4, 4), interpolation="nearest", name="upsampling_stage4")(
        s4
    )
    s3 = layers.UpSampling2D((2, 2), interpolation="nearest", name="upsampling_stage3")(
        s3
    )

    # aggregating results
    x = layers.Add(name="aggregation_sum")([s2, s3, s4, s5])

    # final stage
    x = Conv3x3BnReLU(segmentation_filters, name="final_stage")(x)
    x = layers.UpSampling2D(
        size=(2, 2), interpolation="bilinear", name="final_upsampling"
    )(x)

    # model head (define number of output classes)
    x = layers.Conv2D(
        filters=output_channels,
        kernel_size=3,
        padding="same",
        activation=activation,
        name="head_conv",
    )(x)
    # x = layers.ReLU()(x)

    return tf.keras.Model(inputs=encoder.input, outputs=x, name=f"FPN_{encoder_name}")
