from dataclasses import dataclass
import dataclasses
from typing import Any
from keras_applications import get_submodules_from_kwargs
from requests import get

from segmentation_models.models._common_blocks import Conv2dBn
from segmentation_models.models._utils import freeze_model
from segmentation_models.backbones.backbones_factory import Backbones
from segmentation_models import _KERAS_BACKEND, _KERAS_MODELS, _KERAS_LAYERS, _KERAS_UTILS


@dataclass
class Ctx:
    backend: Any
    models: Any
    layers: Any
    utils: Any

    def to_dict(self):
        result = {}
        for f in dataclasses.fields(self):
            result[f.name] = getattr(self, f.name)
        return result

def get_ctx():
    return Ctx(backend=_KERAS_BACKEND, models=_KERAS_MODELS, layers=_KERAS_LAYERS, utils=_KERAS_UTILS)


# ---------------------------------------------------------------------
#  Blocks
# ---------------------------------------------------------------------

def Conv3x3BnReLU(ctx, filters, use_batchnorm, name=None):
    def wrapper(input_tensor):
        return Conv2dBn(
            filters,
            kernel_size=3,
            activation='relu',
            kernel_initializer='he_uniform',
            padding='same',
            use_batchnorm=use_batchnorm,
            name=name,
            **ctx.to_dict()
        )(input_tensor)

    return wrapper


def DecoderUpsamplingX2Block(ctx, filters, stage, use_batchnorm=False):
    up_name = 'decoder_stage{}_upsampling'.format(stage)
    conv1_name = 'decoder_stage{}a'.format(stage)
    conv2_name = 'decoder_stage{}b'.format(stage)
    concat_name = 'decoder_stage{}_concat'.format(stage)

    concat_axis = 3 if ctx.backend.image_data_format() == 'channels_last' else 1

    def wrapper(input_tensor, skip=None):
        x = ctx.layers.UpSampling2D(size=2, name=up_name)(input_tensor)

        if skip is not None:
            x = ctx.layers.Concatenate(axis=concat_axis, name=concat_name)([x, skip])

        x = Conv3x3BnReLU(ctx, filters, use_batchnorm, name=conv1_name)(x)
        x = Conv3x3BnReLU(ctx, filters, use_batchnorm, name=conv2_name)(x)

        return x

    return wrapper


def DecoderTransposeX2Block(ctx, filters, stage, use_batchnorm=False):
    transp_name = 'decoder_stage{}a_transpose'.format(stage)
    bn_name = 'decoder_stage{}a_bn'.format(stage)
    relu_name = 'decoder_stage{}a_relu'.format(stage)
    conv_block_name = 'decoder_stage{}b'.format(stage)
    concat_name = 'decoder_stage{}_concat'.format(stage)

    concat_axis = bn_axis = 3 if ctx.backend.image_data_format() == 'channels_last' else 1

    def layer(input_tensor, skip=None):

        x = ctx.layers.Conv2DTranspose(
            filters,
            kernel_size=(4, 4),
            strides=(2, 2),
            padding='same',
            name=transp_name,
            use_bias=not use_batchnorm,
        )(input_tensor)

        if use_batchnorm:
            x = ctx.layers.BatchNormalization(axis=bn_axis, name=bn_name)(x)

        x = ctx.layers.Activation('relu', name=relu_name)(x)

        if skip is not None:
            x = ctx.layers.Concatenate(axis=concat_axis, name=concat_name)([x, skip])

        x = Conv3x3BnReLU(ctx, filters, use_batchnorm, name=conv_block_name)(x)

        return x

    return layer


# ---------------------------------------------------------------------
#  Unet Decoder
# ---------------------------------------------------------------------

def build_unet(
    ctx,
    backbone,
    decoder_block,
    skip_connection_layers,
    decoder_filters=(256, 128, 64, 32, 16),
    n_upsample_blocks=5,
    classes=1,
    activation='sigmoid',
    use_batchnorm=True,
):
    input_ = backbone.input
    x = backbone.output

    # extract skip connections
    skips = ([backbone.get_layer(name=i).output if isinstance(i, str)
              else backbone.get_layer(index=i).output for i in skip_connection_layers])

    # add center block if previous operation was maxpooling (for vgg models)
    if isinstance(backbone.layers[-1], ctx.layers.MaxPooling2D):
        x = Conv3x3BnReLU(ctx, 512, use_batchnorm, name='center_block1')(x)
        x = Conv3x3BnReLU(ctx, 512, use_batchnorm, name='center_block2')(x)

    # building decoder blocks
    for i in range(n_upsample_blocks):

        if i < len(skips):
            skip = skips[i]
        else:
            skip = None

        x = decoder_block(ctx, decoder_filters[i], stage=i, use_batchnorm=use_batchnorm)(x, skip)

    # model head (define number of output classes)
    x = ctx.layers.Conv2D(
        filters=classes,
        kernel_size=(3, 3),
        padding='same',
        use_bias=True,
        kernel_initializer='glorot_uniform',
        name='final_conv',
    )(x)
    x = ctx.layers.Activation(activation, name=activation)(x)

    # create keras model instance
    model = ctx.models.Model(input_, x)

    return model


# ---------------------------------------------------------------------
#  Unet Model
# ---------------------------------------------------------------------

def Unet(
    backbone_name='vgg16',
    input_shape=(None, None, 3),
    classes=1,
    activation='sigmoid',
    weights=None,
    encoder_weights='imagenet',
    encoder_freeze=False,
    encoder_features='default',
    decoder_block_type='upsampling',
    decoder_filters=(256, 128, 64, 32, 16),
    decoder_use_batchnorm=True,
):
    """ Unet_ is a fully convolution neural network for image semantic segmentation

    Args:
        backbone_name: name of classification model (without last dense layers) used as feature
            extractor to build segmentation model.
        input_shape: shape of input data/image ``(H, W, C)``, in general
            case you do not need to set ``H`` and ``W`` shapes, just pass ``(None, None, C)`` to make your model be
            able to process images af any size, but ``H`` and ``W`` of input images should be divisible by factor ``32``.
        classes: a number of classes for output (output shape - ``(h, w, classes)``).
        activation: name of one of ``keras.activations`` for last model layer
            (e.g. ``sigmoid``, ``softmax``, ``linear``).
        weights: optional, path to model weights.
        encoder_weights: one of ``None`` (random initialization), ``imagenet`` (pre-training on ImageNet).
        encoder_freeze: if ``True`` set all layers of encoder (backbone model) as non-trainable.
        encoder_features: a list of layer numbers or names starting from top of the model.
            Each of these layers will be concatenated with corresponding decoder block. If ``default`` is used
            layer names are taken from ``DEFAULT_SKIP_CONNECTIONS``.
        decoder_block_type: one of blocks with following layers structure:

            - `upsampling`:  ``UpSampling2D`` -> ``Conv2D`` -> ``Conv2D``
            - `transpose`:   ``Transpose2D`` -> ``Conv2D``

        decoder_filters: list of numbers of ``Conv2D`` layer filters in decoder blocks
        decoder_use_batchnorm: if ``True``, ``BatchNormalisation`` layer between ``Conv2D`` and ``Activation`` layers
            is used.

    Returns:
        ``keras.models.Model``: **Unet**

    .. _Unet:
        https://arxiv.org/pdf/1505.04597

    """
    ctx = get_ctx()

    if decoder_block_type == 'upsampling':
        decoder_block = DecoderUpsamplingX2Block
    elif decoder_block_type == 'transpose':
        decoder_block = DecoderTransposeX2Block
    else:
        raise ValueError('Decoder block type should be in ("upsampling", "transpose"). '
                         'Got: {}'.format(decoder_block_type))

    backbone = Backbones.get_backbone(
        backbone_name,
        input_shape=input_shape,
        weights=encoder_weights,
        include_top=False,
        **ctx.to_dict(),
    )

    if encoder_features == 'default':
        encoder_features = Backbones.get_feature_layers(backbone_name, n=4)

    model = build_unet(
        ctx,
        backbone=backbone,
        decoder_block=decoder_block,
        skip_connection_layers=encoder_features,
        decoder_filters=decoder_filters,
        classes=classes,
        activation=activation,
        n_upsample_blocks=len(decoder_filters),
        use_batchnorm=decoder_use_batchnorm,
    )

    # lock encoder weights for fine-tuning
    if encoder_freeze:
        freeze_model(backbone, **ctx.to_dict())

    # loading model weights
    if weights is not None:
        model.load_weights(weights)

    return model
