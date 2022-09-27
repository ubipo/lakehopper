"""Common preprocessing functionality.

Adapted from:
- https://github.com/dronedeploy/dd-ml-segmentation-benchmark
- https://github.com/chrise96/image-to-coco-json-converter
- https://github.com/jsbroks/imantics
"""

import csv
import json
from pathlib import Path
from typing import Callable, Mapping, Optional
import cv2
from cv2 import Mat
import numpy as np


DEFAULT_CHIP_SIZE_SIDE = 300
DEFAULT_CHIP_STRIDE_SIDE = 300


def image_to_chips(
    image_path,
    label_mask_path,
    size,
    stride,
):
    w, h = size
    stride_x, stride_y = stride
    ortho = cv2.imread(str(image_path))
    label = cv2.imread(str(label_mask_path))

    assert ortho.shape[0] == label.shape[0]
    assert ortho.shape[1] == label.shape[1]

    shape = ortho.shape

    xsize = shape[1]
    ysize = shape[0]
    print(f"Converting image {image_path.stem} {xsize}x{ysize} to chips...")

    for xi in range(0, shape[1] - w, stride_x):
        for yi in range(0, shape[0] - h, stride_y):
            image_chip = ortho[yi : yi + h, xi : xi + w, :]
            color_label_mask_chip = label[yi : yi + h, xi : xi + w, :]
            yield image_chip, color_label_mask_chip


def color_to_categorical_mask(
    img: Mat,
    label_color_map: Mapping[str, tuple],
    labels_to_keep: list[str],
    background_color: tuple,
    ignore_color: Optional[tuple] = None,
):
    categorical_mask = np.zeros((img.shape[0], img.shape[1]), dtype="uint8")
    colors = np.unique(img.reshape(-1, img.shape[2]), axis=0)

    if ignore_color != None:
        # Skip any chips that would contain IGNORE pixels
        seen_colors = set([tuple(color) for color in colors])
        if ignore_color in seen_colors:
            return (), None

    inv_label_color_map = {v: k for k, v in label_color_map.items()}

    nbro_label_pixels = {}
    for color in colors:
        if tuple(color) == background_color:
            continue
        label = inv_label_color_map[tuple(color)]
        locs = np.where(
            (img[:, :, 0] == color[0])
            & (img[:, :, 1] == color[1])
            & (img[:, :, 2] == color[2])
        )
        if label in labels_to_keep:
            nbro_label_pixels[label] = len(locs[0])
            category = labels_to_keep.index(label) + 1
        else:
            category = 0  # background

        categorical_mask[locs[0], locs[1]] = category

    return nbro_label_pixels, categorical_mask


def images_to_chips(
    images_paths: list[Path],
    label_masks_paths: list[Path],
    out_base_path: Path,
    image_path_to_prefix: Callable,
    labels_to_keep: list[int],
    label_color_map: Mapping[str, tuple],
    background_color: tuple,
    ignore_color: tuple,
):
    size = (DEFAULT_CHIP_SIZE_SIDE,) * 2
    stride = (DEFAULT_CHIP_STRIDE_SIDE,) * 2

    image_chips_path = out_base_path / "images"
    label_chips_path = out_base_path / "labels"
    image_chips_path.mkdir(parents=True, exist_ok=True)
    label_chips_path.mkdir(parents=True, exist_ok=True)

    assert len(images_paths) == len(label_masks_paths)

    images_paths.sort(key=lambda p: p.stem)
    label_masks_paths.sort(key=lambda p: p.stem)

    # Mapping from chip filename stems to labels in that chip
    # e.g. 'chunk5-000025.png' -> ('water', 'ground)
    chip_labels = {}

    for image_path, label_mask_path in zip(images_paths, label_masks_paths):
        out_files_prefix = image_path_to_prefix(image_path)
        chips = image_to_chips(
            image_path,
            label_mask_path,
            size=size,
            stride=stride,
        )
        for chip_i, (image_chip, color_label_mask_chip) in enumerate(chips):
            nbro_label_pixels, categorical_mask_chip = color_to_categorical_mask(
                color_label_mask_chip,
                label_color_map,
                labels_to_keep,
                background_color,
                ignore_color,
            )

            if categorical_mask_chip is None:
                continue

            stem = f"{out_files_prefix}-{chip_i:06}"
            chip_labels[stem] = nbro_label_pixels
            filename = stem + ".png"
            cv2.imwrite(str(image_chips_path / filename), image_chip)
            cv2.imwrite(str(label_chips_path / filename), categorical_mask_chip)

    metadata = {"size": size, "stride": stride, "nbroLabelPixels": chip_labels}
    with open(out_base_path / "metadata.json", "w") as f:
        json.dump(metadata, f)
