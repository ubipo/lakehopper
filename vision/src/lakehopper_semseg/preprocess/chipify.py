"""Preprocessing script for the dronedeploy dataset."""

import argparse
from pathlib import Path
import sys

from .colormaps import (
    DRONEDEPLOY_BG_COLOR,
    DRONEDEPLOY_IGNORE_COLOR,
    DRONEDEPLOY_LABEL_COLOR_MAP,
    IV_ORTHO_BG_COLOR,
    IV_ORTHO_MID_LABEL_COLOR_MAP,
)

from .common import images_to_chips

# Need at least 3.7 for ordered dicts (ordering is important for byte masks)
assert sys.version_info > (3, 7)

DATASET_DRONEDEPLOY = "dronedeploy"
DATASET_IV_ORTHO_MID = "iv-ortho-mid"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--dataset",
        required=True,
        choices=[DATASET_DRONEDEPLOY, DATASET_IV_ORTHO_MID],
        type=str,
        help="Dataset to chippify",
    )
    parser.add_argument("-c", "--chips-prefix", type=str, help="Prefix for all chips")
    parser.add_argument("IMAGES_DIR", type=Path, help="Images directory")
    parser.add_argument("LABELS_DIR", type=Path, help="Labels directory")
    parser.add_argument("OUT_DIR", type=Path, help="Output directory")
    args = parser.parse_args()

    dataset = args.dataset
    chips_prefix = args.chips_prefix
    if chips_prefix is None:
        chips_prefix = ""
    else:
        chips_prefix = f"{chips_prefix}-"
    images_dir: Path = args.IMAGES_DIR
    labels_dir: Path = args.LABELS_DIR
    out_dir: Path = args.OUT_DIR

    labels_to_keep = ["water", "building"]

    if dataset == DATASET_DRONEDEPLOY:
        label_color_map = DRONEDEPLOY_LABEL_COLOR_MAP
        background_color = DRONEDEPLOY_BG_COLOR
        ignore_color = DRONEDEPLOY_IGNORE_COLOR
        images_paths = list(images_dir.glob("*-ortho.tif"))
        labels_paths = list(labels_dir.glob("*-label.png"))
        image_path_to_prefix = (
            lambda image_path: chips_prefix + image_path.stem.removesuffix("-ortho")
        )
    elif dataset == DATASET_IV_ORTHO_MID:
        label_color_map = IV_ORTHO_MID_LABEL_COLOR_MAP
        background_color = IV_ORTHO_BG_COLOR
        ignore_color = None
        images_paths = list(images_dir.glob("*.png"))
        labels_paths = list(labels_dir.glob("*.png"))
        image_path_to_prefix = lambda image_path: chips_prefix + image_path.stem
    else:
        raise RuntimeError(f"Unknown dataset: {dataset}")

    images_to_chips(
        images_paths,
        labels_paths,
        out_dir,
        image_path_to_prefix,
        labels_to_keep,
        label_color_map,
        background_color,
        ignore_color,
    )
