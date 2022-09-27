# U-Net model for semantic segmentation.
#
# Ronneberger, O., Fischer, P. and Brox, T. (2015) ‘U-Net: Convolutional
# Networks for Biomedical Image Segmentation’. arXiv. Available at:
# http://arxiv.org/abs/1505.04597 (Accessed: 10 July 2022).
#
# Adapted from:
#  - https://www.tensorflow.org/tutorials/images/segmentation
#  - https://github.com/qubvel/segmentation_models

import tensorflow as tf
import tensorflow.keras.layers as layers

from .encoder import create_encoder
from .blocks import Conv3x3BnReLU


NBRO_UPSAMPLE_BLOCKS = 5
DECODER_FILTERS = (256, 128, 64, 32, 16)


def DecoderUpsamplingX2Block(filters, name):
    def block(input_tensor, skip=None):
        x = layers.UpSampling2D(size=2, name=f"{name}_upsampling")(input_tensor)

        if skip is not None:
            # print("Concatenating skip connection")
            # print(x.shape)
            # print(skip.shape)
            x = layers.Concatenate(name=f"{name}_concat")([x, skip])

        x = Conv3x3BnReLU(filters, name=f"{name}a")(x)
        x = Conv3x3BnReLU(filters, name=f"{name}b")(x)

        return x

    return block


def create_unet(
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

    if isinstance(encoder.layers[-1], layers.MaxPooling2D):
        x = Conv3x3BnReLU(512, name="center_block1")(x)
        x = Conv3x3BnReLU(512, name="center_block2")(x)

    for i in range(NBRO_UPSAMPLE_BLOCKS):
        if i < len(skips):
            skip = skips[i]
        else:
            skip = None

        x = DecoderUpsamplingX2Block(DECODER_FILTERS[i], name=f"decoder_stage_{i}")(
            x, skip
        )

    # model head (define number of output classes)
    x = layers.Conv2D(
        filters=output_channels,
        kernel_size=3,
        padding="same",
        activation=activation,
        name="final_conv",
    )(x)

    return tf.keras.Model(inputs=encoder.input, outputs=x, name=f"UNet_{encoder_name}")
