# FPN model for semantic segmentation
# 
# Lin, T.-Y. et al. (2017) ‘Feature Pyramid Networks for Object Detection’. arXiv. (Accessed: 10 July 2022).
# http://arxiv.org/abs/1612.03144
# 
# Adapted from: https://github.com/qubvel/segmentation_models/blob/master/segmentation_models/models/fpn.py

import tensorflow as tf

from .encoder import create_encoder

def FPNBlock(pyramid_filters, stage):
    conv0_name = 'fpn_stage_p{}_pre_conv'.format(stage)
    conv1_name = 'fpn_stage_p{}_conv'.format(stage)
    add_name = 'fpn_stage_p{}_add'.format(stage)
    up_name = 'fpn_stage_p{}_upsampling'.format(stage)

    def wrapper(input_tensor, skip):
        # if input tensor channels not equal to pyramid channels
        # we will not be able to sum input tensor and skip
        # so add extra conv layer to transform it
        input_filters = tf.keras.backend.int_shape(input_tensor)[3]
        if input_filters != pyramid_filters:
            input_tensor = tf.keras.layers.Conv2D(
                filters=pyramid_filters,
                kernel_size=(1, 1),
                kernel_initializer='he_uniform',
                name=conv0_name,
            )(input_tensor)

        skip = tf.keras.layers.Conv2D(
            filters=pyramid_filters,
            kernel_size=(1, 1),
            kernel_initializer='he_uniform',
            name=conv1_name,
        )(skip)

        x = tf.keras.layers.UpSampling2D((2, 2), name=up_name)(input_tensor)
        x = tf.keras.layers.Add(name=add_name)([x, skip])

        return x

    return wrapper

def Conv2dBn(
        filters,
        kernel_size,
        strides=(1, 1),
        padding='valid',
        data_format=None,
        dilation_rate=(1, 1),
        activation=None,
        kernel_initializer='glorot_uniform',
        bias_initializer='zeros',
        kernel_regularizer=None,
        bias_regularizer=None,
        activity_regularizer=None,
        kernel_constraint=None,
        bias_constraint=None,
        use_batchnorm=False,
        **kwargs
):
    """Extension of Conv2D layer with batchnorm"""

    conv_name, act_name, bn_name = None, None, None
    block_name = kwargs.pop('name', None)

    if block_name is not None:
        conv_name = block_name + '_conv'

    if block_name is not None and activation is not None:
        act_str = activation.__name__ if callable(activation) else str(activation)
        act_name = block_name + '_' + act_str

    if block_name is not None and use_batchnorm:
        bn_name = block_name + '_bn'

    def wrapper(input_tensor):

        x = tf.keras.layers.Conv2D(
            filters=filters,
            kernel_size=kernel_size,
            strides=strides,
            padding=padding,
            data_format=data_format,
            dilation_rate=dilation_rate,
            activation=None,
            use_bias=not (use_batchnorm),
            kernel_initializer=kernel_initializer,
            bias_initializer=bias_initializer,
            kernel_regularizer=kernel_regularizer,
            bias_regularizer=bias_regularizer,
            activity_regularizer=activity_regularizer,
            kernel_constraint=kernel_constraint,
            bias_constraint=bias_constraint,
            name=conv_name,
        )(input_tensor)

        if use_batchnorm:
            x = tf.keras.layers.BatchNormalization(axis=3, name=bn_name)(x)

        if activation:
            x = tf.keras.layers.Activation(activation, name=act_name)(x)

        return x

    return wrapper

def Conv3x3BnReLU(filters, use_batchnorm, name=None):
    def wrapper(input_tensor):
        return Conv2dBn(
            filters,
            kernel_size=3,
            activation='relu',
            kernel_initializer='he_uniform',
            padding='same',
            use_batchnorm=use_batchnorm,
            name=name,
        )(input_tensor)

    return wrapper

def DoubleConv3x3BnReLU(filters, use_batchnorm, name=None):
    name1, name2 = None, None
    if name is not None:
        name1 = name + 'a'
        name2 = name + 'b'

    def wrapper(input_tensor):
        x = Conv3x3BnReLU(filters, use_batchnorm, name=name1)(input_tensor)
        x = Conv3x3BnReLU(filters, use_batchnorm, name=name2)(x)
        return x

    return wrapper

def create_fpn(encoder_name: str, nbro_classes: int, shape: tuple):
    down_stack = create_encoder(encoder_name, shape)

    inputs = tf.keras.layers.Input(shape=shape)

    pyramid_filters = 255
    use_batchnorm=True
    segmentation_filters=128

        # Downsampling through the model
    skips = down_stack(inputs)
    x = skips[-1]
    skips = list(reversed(skips[:-1]))

    p5 = FPNBlock(pyramid_filters, stage=5)(x, skips[0])
    p4 = FPNBlock(pyramid_filters, stage=4)(p5, skips[1])
    p3 = FPNBlock(pyramid_filters, stage=3)(p4, skips[2])
    p2 = FPNBlock(pyramid_filters, stage=2)(p3, skips[3])

    # add segmentation head to each
    s5 = DoubleConv3x3BnReLU(segmentation_filters, use_batchnorm, name='segm_stage5')(p5)
    s4 = DoubleConv3x3BnReLU(segmentation_filters, use_batchnorm, name='segm_stage4')(p4)
    s3 = DoubleConv3x3BnReLU(segmentation_filters, use_batchnorm, name='segm_stage3')(p3)
    s2 = DoubleConv3x3BnReLU(segmentation_filters, use_batchnorm, name='segm_stage2')(p2)

    # upsampling to same resolution
    s5 = tf.keras.layers.UpSampling2D((8, 8), interpolation='nearest', name='upsampling_stage5')(s5)
    s4 = tf.keras.layers.UpSampling2D((4, 4), interpolation='nearest', name='upsampling_stage4')(s4)
    s3 = tf.keras.layers.UpSampling2D((2, 2), interpolation='nearest', name='upsampling_stage3')(s3)

    # aggregating results
    x = tf.keras.layers.Add(name='aggregation_sum')([s2, s3, s4, s5])

    # final stage
    x = Conv3x3BnReLU(segmentation_filters, use_batchnorm, name='final_stage')(x)
    x = tf.keras.layers.UpSampling2D(size=(2, 2), interpolation='bilinear', name='final_upsampling')(x)

    # model head (define number of output classes)
    x = tf.keras.layers.Conv2D(
        filters=nbro_classes,
        kernel_size=(3, 3),
        padding='same',
        use_bias=True,
        kernel_initializer='glorot_uniform',
        name='head_conv',
    )(x)
    x = tf.keras.layers.ReLU()(x)

    return tf.keras.Model(inputs=inputs, outputs=x)
