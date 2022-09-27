import tensorflow as tf
from .blocks import Conv2DBn
import tensorflow.keras.applications as app
import tensorflow.keras.layers as layers


def create_encoder(encoder_name: str, shape: tuple, trainable: bool = False):
    """Encoder inputs must be in the [0-255] range."""

    model_kwargs = dict(include_top=False, weights="imagenet")
    if encoder_name == "MobileNetV2":
        input_layer = layers.Input(shape, dtype=tf.float32, name="top_input")
        preprocessed = app.mobilenet.preprocess_input(input_layer)
        encoder = app.mobilenet_v2.MobileNetV2(
            input_tensor=preprocessed, input_shape=shape, **model_kwargs
        )
        skip_layer_names = [
            "block_1_expand_relu",
            "block_3_expand_relu",
            "block_6_expand_relu",
            "block_13_expand_relu",
        ]
        skip_layers = [encoder.get_layer(name).output for name in skip_layer_names]
        output = encoder.outputs[-1]
    elif encoder_name == "EfficientNetB3":
        # No preprocessing needed
        encoder = app.EfficientNetB3(input_shape=shape, **model_kwargs)
        skip_layer_names = [
            "block2a_expand_activation",
            "block3a_expand_activation",
            "block4a_expand_activation",
            "block6a_expand_activation",
        ]
        skip_layers = [encoder.get_layer(name).output for name in skip_layer_names]
        output = encoder.outputs[-1]
    elif encoder_name == "InceptionResNetV2":
        input_layer = layers.Input(shape, dtype=tf.float32)
        preprocessed = app.inception_resnet_v2.preprocess_input(input_layer)
        encoder = app.inception_resnet_v2.InceptionResNetV2(
            input_tensor=preprocessed, **model_kwargs
        )
        # Layers are not named; use filter depth instead
        activation_layer_depths = [64, 192, 320, 1088]
        # Correct for padding=valid of tensorflow's InceptionResNetV2
        # See: https://github.com/keras-team/keras-applications/blob/master/keras_applications/inception_resnet_v2.py
        skip_kernel_sizes = [4, 5, 4, 3]
        skip_layers = [
            layers.Conv2DTranspose(depth, kernel_size, strides=1)(
                next(
                    layer.output
                    for layer in encoder.layers
                    if isinstance(layer, layers.Activation)
                    and layer.output_shape[-1] == depth
                )
            )
            for depth, kernel_size in zip(activation_layer_depths, skip_kernel_sizes)
        ]
        # skip_layers[3] = skip_layers[3]
        output = encoder.outputs[-1]
        output = layers.Conv2DTranspose(output.shape[-1], 3)(output)
    elif encoder_name == "ResNet50":
        input_layer = layers.Input(shape, dtype=tf.float32, name="top_input")
        preprocessed = app.resnet50.preprocess_input(input_layer)
        encoder = app.resnet50.ResNet50(input_tensor=preprocessed, **model_kwargs)
        skip_layer_names = [
            "conv1_relu",
            "conv2_block3_out",
            "conv3_block4_out",
            "conv4_block6_out",
        ]
        skip_layers = [encoder.get_layer(name).output for name in skip_layer_names]
        output = encoder.outputs[-1]
    else:
        raise ValueError(f"Unknown encoder name: {encoder_name}")

    encoder.trainable = trainable

    return (encoder, output, skip_layers)
