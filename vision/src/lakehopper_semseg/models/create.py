import tensorflow as tf
import tensorflow.keras.metrics as k_metrics
import tensorflow.keras.activations as k_activations
from .unet import create_unet
from .fcn import create_fcn8
from .fpn import create_fpn
from .f1score import F1Score


def create_model(classes, input_shape, encoder_name, decoder_name) -> tf.keras.Model:
    nbro_classes = len(classes)
    if nbro_classes > 1:
        nbro_classes += 1  # Add background class
    activation = k_activations.sigmoid if nbro_classes == 1 else k_activations.softmax
    create_model_kwargs = dict(
        encoder_name=encoder_name,
        output_channels=nbro_classes,
        input_shape=input_shape,
        activation=activation,
        encoder_trainable=True,
    )
    if decoder_name == "UNet":
        return create_unet(**create_model_kwargs)
    elif decoder_name == "FCN":
        return create_fcn8(**create_model_kwargs)
    elif decoder_name == "FPN":
        return create_fpn(**create_model_kwargs)
    else:
        raise ValueError(f"Unknown decoder: {decoder_name}")


def compile_model(model, classes):
    learning_rate = 0.0001
    nbro_classes = len(classes)
    if nbro_classes > 1:
        nbro_classes += 1  # Add background class
    optimizer = tf.keras.optimizers.Adam(learning_rate)
    loss = (
        tf.keras.losses.BinaryFocalCrossentropy()
        if nbro_classes == 1
        else tf.keras.losses.CategoricalCrossentropy()
    )
    # fmt: off
    metrics = [
        F1Score(),
        k_metrics.Precision(),
        k_metrics.Recall(),
        *([
            k_metrics.CategoricalAccuracy(name="accuracy"),
            k_metrics.OneHotIoU(
                name="mean_iou",
                num_classes=nbro_classes,
                # Ignore background class
                # ignore_class=0,
                target_class_ids=list(range(0, nbro_classes))
            ),
        ] if nbro_classes > 1 else [
            k_metrics.BinaryAccuracy(name="accuracy")
        ]),
    ]
    # fmt: on
    model.compile(optimizer=optimizer, loss=loss, weighted_metrics=metrics)
    return model
