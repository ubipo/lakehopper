import tensorflow.keras.layers as layers


def Conv2DBn(
    filters,
    kernel_size,
    name,
    activation,
    padding="valid",
    dilation_rate=(1, 1),
    kernel_initializer="glorot_uniform",
):
    """Extension of Conv2D layer with batchnorm"""

    def block(input_tensor):
        x = layers.Conv2D(
            filters=filters,
            kernel_size=kernel_size,
            padding=padding,
            dilation_rate=dilation_rate,
            use_bias=False,
            kernel_initializer=kernel_initializer,
            name=f"{name}_conv",
        )(input_tensor)

        x = layers.BatchNormalization(name=f"{name}_bn")(x)
        x = layers.Activation(activation, name=f"{name}_{activation}")(x)

        return x

    return block


def Conv3x3BnReLU(filters, name):
    return Conv2DBn(
        filters,
        kernel_size=3,
        name=name,
        activation="relu",
        kernel_initializer="he_uniform",
        padding="same",
    )
