"""Convenience functions to train on [Google Cloud
Platform](https://cloud.google.com/)'s "[TPU's](https://cloud.google.com/tpu)".
TPU's use a machine learning ASIC.
"""

import tensorflow as tf
from tensorflow.python.distribute.tpu_strategy import TPUStrategy


def resolve_tpu_strategy(tpu: str) -> TPUStrategy:
    resolver = tf.distribute.cluster_resolver.TPUClusterResolver.connect(tpu)
    return tf.distribute.TPUStrategy(resolver)

def get_tpu_devices():
    return tf.config.list_logical_devices('TPU')
