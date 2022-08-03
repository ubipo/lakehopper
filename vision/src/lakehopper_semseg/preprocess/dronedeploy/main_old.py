"""Preprocessing script for the dronedeploy dataset.

Adapted from:
- https://github.com/dronedeploy/dd-ml-segmentation-benchmark
- https://github.com/chrise96/image-to-coco-json-converter
- https://github.com/jsbroks/imantics
"""

import argparse
import json
from pathlib import Path
import sys
from typing import Mapping
# import images2chips
import skimage
import cv2
import numpy as np
from imantics import Polygons, Mask
from shapely.geometry import Polygon
import pycocotools.mask as cocomask

LABELS = ['IGNORE', 'BUILDING', 'CLUTTER', 'VEGETATION', 'WATER', 'GROUND', 'CAR']

# Class to color (BGR)
LABELMAP = {
    0 : (255,   0, 255),
    1 : (75,   25, 230),
    2 : (180,  30, 145),
    3 : (75,  180,  60),
    4 : (48,  130, 245),
    5 : (255, 255, 255),
    6 : (200, 130,   0),
}

# Color (BGR) to class
INV_LABELMAP = {
    (255,   0, 255) : 0,
    (75,   25, 230) : 1,
    (180,  30, 145) : 2,
    (75,  180,  60) : 3,
    (48,  130, 245) : 4,
    (255, 255, 255) : 5,
    (200, 130,   0) : 6,
}

LABELMAP_RGB = { k: (v[2], v[1], v[0]) for k, v in LABELMAP.items() }

INV_LABELMAP_RGB = { v: k for k, v in LABELMAP_RGB.items() }

def color2class_masks(img):
    ret = np.zeros((img.shape[0], img.shape[1]), dtype='uint8')
    colors = np.unique(img.reshape(-1, img.shape[2]), axis=0)

    # Skip any chips that would contain magenta (IGNORE) pixels
    # seen_colors = set( [tuple(color) for color in colors] )
    # IGNORE_COLOR = LABELMAP[0]
    # if IGNORE_COLOR in seen_colors:
    #     return None, None
    label_color_tuples = [(LABELS[INV_LABELMAP[tuple(color)]], tuple(color)) for color in colors]
    print(label_color_tuples)

    class_masks = {}

    for color in colors:
        label = LABELS[INV_LABELMAP[tuple(color)]]
        locs = np.where((img[:, :, 0] == color[0]) & (img[:, :, 1] == color[1]) & (img[:, :, 2] == color[2]))
        class_mask = np.zeros((img.shape[0], img.shape[1]), dtype='uint8')
        class_mask[locs[0], locs[1]] = 255
        class_masks[label] = class_mask
    

    # for color in colors:
    #     locs = np.where((img[:, :, 0] == color[0]) & (img[:, :, 1] == color[1]) & (img[:, :, 2] == color[2]))
    #     ret[locs[0], locs[1]] = INV_LABELMAP[tuple(color)] - 1

    return class_masks

def get_image_mask_path_tuple(image_path: Path):
    scene = image_path.stem.removesuffix('-ortho')
    label_mask_path = (image_path.parent.parent / 'labels' / f'{scene}-label.png')
    return (scene, image_path, label_mask_path)

def get_image_mask_path_tuples(prefix: Path):
    image_paths = (prefix / 'images').glob('*.tif')
    return [get_image_mask_path_tuple(image_path) for image_path in image_paths]

def run_images_to_chips():
    print(f"converting {len(image_paths)} images to chips - this may take a few minutes but only needs to be done once.")
    (prefix / 'image-chips').mkdir(exist_ok=True)
    (prefix / 'label-chips').mkdir(exist_ok=True)

def mask_to_polygons(mask: np.ndarray):
    # for (scene, image_path, label_mask_path) in get_image_mask_path_tuples(path):
    class_masks = color2class_masks(mask)
    class_polygons = {}

    for label, class_mask in class_masks.items():
        rle = cocomask.encode(np.asfortranarray(class_mask))
        print(rle)

        

        sys.exit()

        buffered = cv2.copyMakeBorder(class_mask, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
        contours, hierarchy = cv2.findContours(buffered, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE, offset=(-1, -1))

        # Map of outer contour index to rings of contour polygon as: (outer, inners[])
        contour_rings: Mapping[str, tuple[any, list[any]]] = {}
        for i, (_i_next, _i_prev, _child_i, parent_i) in enumerate(hierarchy[0]):
            ring = [tuple(coord[0]) for coord in contours[i]]
            
            if len(ring) < 3:
                continue

            is_outer_ring = parent_i == -1
            if is_outer_ring:
                outer = ring
                inners = []
                contour_rings[i] = (outer, inners)
            else:
                outer, inners = contour_rings[parent_i]
                inners.append(ring)

        polygons = []
        for outer, inners in contour_rings.values():
            polygon = Polygon(outer, inners)
            polygon.simplify(1.0, preserve_topology=False)
            if(polygon.is_empty):
                continue
            polygons.append(polygon)

        if len(polygons) == 0:
            continue
        
        class_polygons[label] = polygons

    return class_polygons

# Adapted from https://github.com/jsbroks/imantics
def mask_to_coco_annotations(path: Path, last_annotation_id: int, label_category_id_map: Mapping[str, int]):
    label_mask_path = Path('/data/projects/lakehopper/segmentation/datasets/dataset-medium/labels/f0747ed88d_E74C0DD8FDOPENPIPELINE-label.png')
    print(label_mask_path)
    mask = cv2.imread(str(label_mask_path))
    class_polygons = mask_to_polygons(mask)
    annotations = []
    for label_i, (label, polygons) in enumerate(class_polygons.items()):
        category_id = label_category_id_map[label]
        for polygon_i, polygon in enumerate(polygons):
            min_x, min_y, max_x, max_y = polygon.bounds
            width = max_x - min_x
            height = max_y - min_y
            bbox = (min_x, min_y, width, height)
            area = polygon.area
            segmentation = np.array(polygon.exterior.coords).ravel().tolist()
            # print(segmentation)
            annotation = {
                "segmentation": segmentation,
                "area": area,
                "iscrowd": 0,
                "image_id": path.stem,
                "bbox": bbox,
                "category_id": category_id,
                "id": last_annotation_id + label_i + polygon_i
            }
            print(annotation)
            sys.exit()
            annotations.append({
                "segmentation": segmentation,
                "area": area,
                "iscrowd": 0,
                "image_id": path.stem,
                "bbox": bbox,
                "category_id": category_id,
                "id": last_annotation_id + label_i + polygon_i
            })

    print(annotations)

    # print(classes)
    # car_class = classes['BUILDING']
    # print(classes.shape)
    # buffered = cv2.copyMakeBorder(car_class, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    # polygons, _ = cv2.findContours(buffered, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE, offset=(-1, -1))
    # polygons = [polygon.flatten() for polygon in polygons]
    # annotations = []
    # for polygon in polygons:
    #     annotations.append({
    #         'segmentation': [polygon],
    #         'area': cv2.contourArea(polygon),
    #         'iscrowd': 0,
    #         'image_id': image_id,
    #         'bbox': [0, 0, 0, 0],
    #         'category_id': category_id,
    #     })
    # print(polygons)
    # print(len(polygons[0]))
    sys.exit()

    # mask = self.array.astype(np.uint8)
    # mask = cv2.copyMakeBorder(mask, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    # polygons = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE, offset=(-1, -1))
    # polygons = polygons[0] if len(polygons) == 2 else polygons[1]
    # polygons = [polygon.flatten() for polygon in polygons]
    # sub_masks = create_sub_masks(mask)
    # for sub_mask in sub_masks:
    #     annotations = create_sub_mask_annotation(sub_mask)
    #     for annotation in annotations:
    #         print(annotation)
    # label_mask = cv2.imread(str(label_mask_path))
    # print(label_mask)
    # print(label_mask.dtype)
    # polygons = Mask(label_mask).polygons()
    # print(polygons)

def labels_to_coco_categories(labels: list[str]):
    return [
        {
            "id": i,
            "name": label,
            "supercategory": "none"
        }
        for i, label in enumerate(labels)
    ]

if __name__ == '__main__':
    parser = argparse.ArgumentParser('dronedeploy-preprocess')
    parser.add_argument('PATH', type=Path, help='Dataset path')
    args = parser.parse_args()

    path = args.PATH

    categories = labels_to_coco_categories(LABELS)
    label_category_id_map = {category['name']: category['id'] for category in categories}

    label_mask_path = Path('/data/projects/lakehopper/segmentation/datasets/dataset-medium/labels/ebffe540d0_7BA042D858OPENPIPELINE-label.png')
    print(label_mask_path)
    mask = cv2.imread(str(label_mask_path))
    class_masks = color2class_masks(mask)
    label, class_mask = list(class_masks.items())[0]
    rle = cocomask.encode(np.asfortranarray(class_mask))
    print(rle)
    w, h = class_mask.shape
    category_id = label_category_id_map[label]
    print(cocomask.toBbox(rle))
    annotation = {
        "segmentation": {
            "size": [int(a) for a in rle["size"]],
            "counts": str(rle["counts"].decode('utf-8'))
        },
        "area": int(cocomask.area(rle)),
        "iscrowd": 0,
        "image_id": path.stem,
        "bbox": [int(a) for a in cocomask.toBbox(rle)],
        "category_id": category_id,
        "id": 0
    }

    with open('cocojson.json', 'w') as f:
        f.write(json.dumps({
            "info":{
                "year":2022,
                "date_created":"2022-07-03T15:46:33Z",
                "version":"1.0",
                "description":"dronedeploy None",
                "contributor":"",
                "url":"https://app.hasty.ai/projects/5a9ed68f-e261-49b6-a9d0-2eaa73ddcc22"
            },
            "licenses":[
                
            ],
            "categories": categories,
            "images":[
                {
                    "id":1,
                    "width":2389,
                    "height":2867,
                    "file_name":"ebffe540d0_7BA042D858OPENPIPELINE-ortho.tif",
                    "license": None,
                    "flickr_url":"",
                    "coco_url": None,
                    "date_captured":"2022-07-03T17:56:47Z"
                },
            ],
            "annotations":[
                annotation
            ]
        }))

    # mask_to_coco_annotations(path, 0, label_category_id_map)
