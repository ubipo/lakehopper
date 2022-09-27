import argparse
import json
from pathlib import Path
import shutil


def aggregate_chip_dirs(
    chip_dirs: list[Path], out_dir: Path, required_labels: list[str]
):
    nbro_label_pixels_merged = {}
    metadata_merged = {"nbroLabelPixels": nbro_label_pixels_merged}
    for chip_dir in chip_dirs:
        with open(chip_dir / "metadata.json") as metadata_f:
            metadata = json.load(metadata_f)
        nbro_label_pixels = metadata["nbroLabelPixels"]
        size = metadata["size"]
        stride = metadata["stride"]
        if "size" not in metadata_merged:
            metadata_merged["size"] = size
            metadata_merged["stride"] = stride
        else:
            assert metadata_merged["size"] == size
            assert metadata_merged["stride"] == stride

        for subdir_name in ["images", "labels"]:
            out_subdir = out_dir / subdir_name
            out_subdir.mkdir(parents=True, exist_ok=True)
            for filename in (chip_dir / subdir_name).iterdir():
                if filename.stem in metadata_merged:
                    raise Exception("Duplicate stem")
                if required_labels is not None:
                    nbro_label_pixels = nbro_label_pixels[filename.stem]
                    if not all(label in nbro_label_pixels for label in required_labels):
                        continue
                shutil.copy(filename, out_subdir)
                nbro_label_pixels_merged[filename.stem] = nbro_label_pixels[
                    filename.stem
                ]

    with open(out_dir / "metadata.json", "w+") as metadata_merged_f:
        json.dump(metadata_merged, metadata_merged_f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-l",
        "--label",
        nargs="+",
        help="Optional minimally required labels. Will skip any images that do not contain all of the specified labels.",
    )
    parser.add_argument(
        "-c",
        "--chip-dir",
        nargs="+",
        type=Path,
        help="Chip directories. Should each contain 'labels' and 'images' subdirectories.",
        required=True,
    )
    parser.add_argument(
        "-o",
        "--out-dir",
        type=Path,
        help="Aggregated output directory.",
        required=True,
    )

    args = parser.parse_args()
    chip_dirs = args.chip_dir
    out_dir = args.out_dir
    required_labels = args.label
    aggregate_chip_dirs(chip_dirs, out_dir, required_labels)
