"""Converts two directories with images and label masks to a single directory
with tfr (tensorflow record) files.

Usage: `to_tfr.py <IMAGES> <LABEL MASKS> <OUT_DIR>`
    IMAGES: directory with images
    LABEL MASKS: directory with label masks
    OUT_DIR: directory to write tfr files to

Files in the images and label mask directories will be correlated according to
their alphabetical order. There must be the same amount of files in each of the
directories. The images and masks should have the same resolution.

See: https://www.tensorflow.org/tutorials/load_data/tfrecord
"""

import argparse
from pathlib import Path

import tensorflow as tf


def _to_bytestring_feature(list_of_bytestrings):
  return tf.train.Feature(bytes_list=tf.train.BytesList(value=list_of_bytestrings))


def image_to_tfr(image_path: Path, label_mask_path: Path, tfr_path: Path):
    with (
        open(image_path, 'rb') as image_file,
        open(label_mask_path, 'rb') as label_mask_file,
        tf.io.TFRecordWriter(str(tfr_path)) as tfr_file
    ):
        feature = {
            "image": _to_bytestring_feature([image_file.read()]),
            "label_mask": _to_bytestring_feature([label_mask_file.read()])
        }
        tf_record = tf.train.Example(features=tf.train.Features(feature=feature))
        tfr_file.write(tf_record.SerializeToString())


def images_to_tfr(images_dir: Path, labels_dir: Path, tfr_dir: Path):
    tfr_dir.mkdir(parents=True, exist_ok=True)
    
    images_paths = sorted(images_dir.iterdir())
    label_masks_paths = sorted(labels_dir.iterdir())
    assert(len(images_paths) == len(label_masks_paths))
    
    for image_path, label_mask_path in zip(images_paths, label_masks_paths):
        assert(image_path.stem == label_mask_path.stem)
        image_to_tfr(image_path, label_mask_path, tfr_dir / f"{image_path.stem}.tfr")



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("images_dir", type=Path)
    parser.add_argument("labels_dir", type=Path)
    parser.add_argument("tfr_dir", type=Path)
    args = parser.parse_args()

    images_to_tfr(args.images_dir, args.labels_dir, args.tfr_dir)
