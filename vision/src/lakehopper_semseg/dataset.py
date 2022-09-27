import json
from typing import Mapping
import tensorflow as tf
from tensorflow.python.data.ops.dataset_ops import Dataset
from pathlib import Path
import numpy as np


@tf.function
def read_tfrecord(tfrecord, image_size):
    features = {
        "image": tf.io.FixedLenFeature([], tf.string),
        "label_mask": tf.io.FixedLenFeature([], tf.string),
    }
    data = tf.io.parse_single_example(tfrecord, features)

    image = tf.image.decode_jpeg(data["image"], channels=3)
    # No cast to float32 necessary, as bilinear resize already does that
    # Also not mapping to [0, 1] by dividing by 255. This is done by the
    # encoder's preprocessing layer.
    image = tf.image.resize(image, image_size, method="bilinear")

    label_mask = tf.image.decode_png(data["label_mask"], channels=1)
    label_mask = tf.image.resize(label_mask, image_size, method="nearest")

    return image, label_mask


def read_metadata(metadata_path: str):
    with tf.io.gfile.GFile(metadata_path) as metadata_f:
        return json.load(metadata_f)


@tf.function
def load_dataset(filenames, image_size, parallel_ops) -> Dataset:
    # read from TFRecords. For optimal performance, read from multiple
    # TFRecord files at once and set the option experimental_deterministic = False
    # to allow order-altering optimizations.

    option_no_order = tf.data.Options()
    option_no_order.experimental_deterministic = False

    dataset = tf.data.TFRecordDataset(filenames, num_parallel_reads=parallel_ops)
    dataset = dataset.with_options(option_no_order)
    dataset = dataset.map(
        lambda tfrecord: read_tfrecord(tfrecord, image_size),
        num_parallel_calls=parallel_ops,
    )
    return dataset


def has_all_classes(tfr_path: str, metadata, required_labels: list[str]) -> list[str]:
    nbro_label_pixels = metadata["nbroLabelPixels"]
    stem = Path(tfr_path).stem
    labels_present = nbro_label_pixels[stem]
    return all(required_label in labels_present for required_label in required_labels)


def has_any_of_classes(
    tfr_path: str, metadata, required_labels: list[str]
) -> list[str]:
    nbro_label_pixels = metadata["nbroLabelPixels"]
    stem = Path(tfr_path).stem
    labels_present = nbro_label_pixels[stem]
    return any(required_label in labels_present for required_label in required_labels)


def split_dataset_paths(paths: list[str], train_ratio: float, validation_ratio: float):
    training_split = train_ratio
    validation_split = train_ratio + validation_ratio
    valid_index = int(len(paths) * training_split)
    test_index = int(len(paths) * validation_split)
    train_paths = paths[:valid_index]
    validate_paths = paths[valid_index:test_index]
    test_paths = paths[test_index:]
    return train_paths, validate_paths, test_paths


def byte_mask_to_single_label_mask(mask: np.mat, label_value: int):
    single_label_mask = np.zeros(mask.shape[:2], dtype=np.float32)
    label_pixels = np.where(mask[:, :] == label_value)
    single_label_mask[label_pixels[0], label_pixels[1]] = 1
    return single_label_mask


@tf.function
def categorical_to_single_label_mask_tf(label, mask):
    # label_mask_single = tf.zeros(label.shape[:2], tf.float32)
    label_mask_single = tf.where(
        mask[:, :] == label,
        tf.ones_like(mask, dtype=tf.float32),
        tf.zeros_like(mask, dtype=tf.float32),
    )
    return label_mask_single


@tf.function
def categorical_to_one_hot_label_mask(nbro_classes: int, mask):
    return tf.one_hot(
        mask[:, :, 0], nbro_classes, dtype=tf.uint8, axis=len(mask.shape) - 1
    )


@tf.function
def single_hot_to_categorical(nbro_classes: int, threshold: float, single_hot_mask):
    # categorical = tf.zeros(single_hot_mask.shape[:-1], tf.uint8)
    # for i in range(nbro_classes):
    #     categorical = tf.where(
    #         single_hot_mask[:, :, i] >= threshold,
    #         tf.ones_like(categorical) * (i + 1),
    #         categorical,
    #     )
    return tf.argmax(single_hot_mask, axis=-1)


@tf.function
def categorical_to_color_mask(
    categorical_mask,
    classes: list[str],
    label_color_map: Mapping[str, tuple],
    background_color: tuple,
):
    categorical_mask_reshaped = categorical_mask[:, :, tf.newaxis]
    color_mask = tf.broadcast_to(background_color, categorical_mask.shape + (3,))
    print(color_mask)
    for i, label in enumerate(classes):
        color_mask = tf.where(
            categorical_mask_reshaped == i + 1,  # +1 because 0 is background
            tf.broadcast_to(label_color_map[label], categorical_mask.shape + (3,)),
            color_mask,
        )
    return color_mask


@tf.function
def single_hot_to_color_mask(
    single_hot_mask,
    classes: list[str],
    label_color_map: Mapping[str, tuple],
    background_color: tuple,
):
    categorical_mask = single_hot_to_categorical(len(classes), 0.8, single_hot_mask)
    return categorical_to_color_mask(
        categorical_mask, classes, label_color_map, background_color
    )
