import tensorflow as tf

def create_encoder(encoder_name: str, shape: tuple):
    if encoder_name == 'MobileNetV2':
        base_model_fn = tf.keras.applications.MobileNetV2
        layer_names = [
            'block_4_depthwise_relu',
            'block_8_depthwise_relu',
            'block_12_depthwise_relu',
            'block_16_depthwise_relu',
        ]
    elif encoder_name == 'EfficientNetB3':
        base_model_fn = tf.keras.applications.EfficientNetB3
        layer_names = [
            'block4e_add',
            'block5e_add',
            'block6f_add',
            'block7b_add',
        ]
    elif encoder_name == 'InceptionResNetV2':
        base_model_fn = tf.keras.applications.InceptionResNetV2
        layer_names = [
            'block35_10_ac',
            'block17_20_ac',
            'block8_9_ac',
            'block8_10',
        ]
    elif encoder_name == 'ResNet50':
        base_model_fn = tf.keras.applications.ResNet50
        layer_names = [
            'conv2_block3_2_relu',
            'conv3_block4_2_relu',
            'conv4_block6_2_relu',
            'conv5_block3_2_relu',
        ]
    else:
        raise ValueError(f'Unknown encoder name: {encoder_name}')

    base_model = base_model_fn(input_shape=shape, include_top=False)
    base_model_outputs = [base_model.get_layer(name).output for name in layer_names]

    # Create the feature extraction model
    down_stack = tf.keras.Model(inputs=base_model.input, outputs=base_model_outputs)

    down_stack.trainable = False

    return down_stack
