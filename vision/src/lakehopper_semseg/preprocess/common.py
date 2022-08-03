"""Common preprocessing functionality.

Adapted from:
- https://github.com/dronedeploy/dd-ml-segmentation-benchmark
- https://github.com/chrise96/image-to-coco-json-converter
- https://github.com/jsbroks/imantics
"""

import csv
from pathlib import Path
from typing import Callable, Mapping, Optional
import cv2
from cv2 import Mat
import numpy as np


DEFAULT_CHIP_SIZE   = 300
DEFAULT_CHIP_STRIDE = 300


def image_to_chips(
    image_path,
    label_mask_path,
    window_x=DEFAULT_CHIP_SIZE,
    window_y=DEFAULT_CHIP_SIZE,
    stride_x=DEFAULT_CHIP_STRIDE,
    stride_y=DEFAULT_CHIP_STRIDE
):
    ortho = cv2.imread(str(image_path))
    label = cv2.imread(str(label_mask_path))

    assert(ortho.shape[0] == label.shape[0])
    assert(ortho.shape[1] == label.shape[1])

    shape = ortho.shape

    xsize = shape[1]
    ysize = shape[0]
    print(f"Converting image {image_path.stem} {xsize}x{ysize} to chips...")

    for xi in range(0, shape[1] - window_x, stride_x):
        for yi in range(0, shape[0] - window_y, stride_y):
            image_chip = ortho[yi:yi+window_y, xi:xi+window_x, :]
            color_label_mask_chip = label[yi:yi+window_y, xi:xi+window_x, :]
            yield image_chip, color_label_mask_chip


def color_to_label_byte_mask(
    img: Mat, label_color_map: Mapping[str, tuple], labels_to_keep: list[str],
    replacement_label: str, ignore_color: Optional[tuple]
):
    label_byte_mask = np.zeros((img.shape[0], img.shape[1]), dtype='uint8')
    colors = np.unique(img.reshape(-1, img.shape[2]), axis=0)

    if ignore_color != None:
        # Skip any chips that would contain IGNORE pixels
        seen_colors = set([tuple(color) for color in colors])
        if ignore_color in seen_colors:
            return (), None

    inv_label_color_map = { v: k for k, v in label_color_map.items() }

    labels_in_mask = set()
    for color in colors:
        label = inv_label_color_map[tuple(color)]
        labels_in_mask.add(label)
        locs = np.where((img[:, :, 0] == color[0]) & (img[:, :, 1] == color[1]) & (img[:, :, 2] == color[2]))
        if label not in labels_to_keep:
            byte = labels_to_keep.index(replacement_label)
        else:
            byte = labels_to_keep.index(label)

        label_byte_mask[locs[0], locs[1]] = byte

    return labels_in_mask, label_byte_mask


def images_to_chips(
    images_paths: list[Path], label_masks_paths: list[Path],
    out_base_path: Path, image_path_to_prefix: Callable,
    labels_to_keep: list[int], replacement_label: int,
    label_color_map: Mapping[str, tuple], ignore_color: tuple
):
    image_chips_path = out_base_path / 'images'
    label_chips_path = out_base_path / 'labels'
    image_chips_path.mkdir(parents=True, exist_ok=True)
    label_chips_path.mkdir(parents=True, exist_ok=True)

    assert len(images_paths) == len(label_masks_paths)

    images_paths.sort(key=lambda p: p.stem)
    label_masks_paths.sort(key=lambda p: p.stem)

    # Mapping from chip filenames to labels in that chip
    # e.g. 'chunk5-000025.png' -> ('water', 'ground)
    chip_labels = {}

    for image_path, label_mask_path in zip(images_paths, label_masks_paths):
        out_files_prefix = image_path_to_prefix(image_path)
        chips = image_to_chips(image_path, label_mask_path)
        for chip_i, (image_chip, color_label_mask_chip) in enumerate(chips):
            labels_in_mask, label_byte_mask_chip = color_to_label_byte_mask(
                color_label_mask_chip, label_color_map,
                labels_to_keep, replacement_label, ignore_color
            )

            if label_byte_mask_chip is None:
                continue

            filename = f'{out_files_prefix}-{chip_i:06}.png'
            chip_labels[filename] = labels_in_mask
            cv2.imwrite(str(image_chips_path / filename), image_chip)
            cv2.imwrite(str(label_chips_path / filename), label_byte_mask_chip)

    with open(out_base_path / 'labels-in-mask.csv', 'w') as f:
        labels = sorted(label_color_map.keys())
        writer = csv.DictWriter(f, fieldnames=['filename', *labels])
        writer.writeheader()
        for filename, labels_in_mask in chip_labels.items():
            row = {'filename': filename}
            for label in labels:
                row[label] = 1 if label in labels_in_mask else 0
            writer.writerow(row)
