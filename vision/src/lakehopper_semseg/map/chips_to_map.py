import csv
import json
from pathlib import Path
import sys
import tensorflow as tf
import numpy as np
import cv2
from skimage import measure
import shapely
from shapely.geometry import Polygon
from typing import Callable, Mapping

IMAGE_SIZE = [128, 128]
LABELS = ['building', 'water', 'ground']

def class_mask_to_polygons(mask, coord_mapper: Callable) -> list[Polygon]:
    buffered = cv2.copyMakeBorder(mask, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
    contours, hierarchy = cv2.findContours(buffered, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE, offset=(-1, -1))

    # Map of outer contour index to rings of contour polygon as: (outer, inners[])
    contour_rings: Mapping[str, tuple[any, list[any]]] = {}
    for i, (_i_next, _i_prev, _child_i, parent_i) in enumerate(hierarchy[0]):
        ring = [coord_mapper(tuple(coord[0])) for coord in contours[i]]
        
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

    return polygons


def mask_to_polygons(mask: np.dtype, label: str, coord_mapper) -> list[Polygon]:
    label_byte = LABELS.index(label)
    locs = np.where(mask == label_byte)
    mask = np.zeros(mask.shape[:2], dtype=np.uint8)
    mask[locs[0], locs[1]] = 1
    polygons = class_mask_to_polygons(mask, coord_mapper)
    return polygons


def read_coord_lookup_table(path: Path):
    lookup_table = {}
    with open(str(path), 'r') as f:
        reader = csv.reader(f)
        next(reader) # skip header
        for row in reader:
            chip_filename = row[0]
            x = float(row[1])
            y = float(row[2])
            lookup_table[chip_filename] = (x, y)
    
    return lookup_table


def chips_to_polygons(model: tf.keras.Model, chips_dir: Path, coord_lookup_table_path: Path):
    building_polygons = []
    water_polygons = []

    for chip_path in chips_dir.glob('*.png'):
        chip = cv2.imread(str(chip_path))
        mask = predict(model, chip)
        chip_x, chip_y = coord_lookup_table_path[chip_path.name]
        coord_mapper = lambda coord: (chip_x + coord[0], chip_y + coord[1])
        building_polygons.extend(mask_to_polygons(mask, 'building', coord_mapper))
        water_polygons.extend(mask_to_polygons(mask, 'water', coord_mapper))

    return building_polygons, water_polygons
        

def opencv_to_model_img(img: np.dtype):
    resized = tf.image.resize(img, IMAGE_SIZE)
    cast = tf.cast(resized, tf.float32) / 255.0
    return cast


def model_prediction_to_mask(size: tuple, model_pred: tf.Tensor) -> np.dtype:
    pred_mask = tf.math.argmax(model_pred, axis=-1)
    return pred_mask.numpy().astype('uint8')


def predict(model: tf.keras.Model, img: np.dtype) -> np.dtype:
    predictions = model(np.asarray([opencv_to_model_img(img)]))
    mask = model_prediction_to_mask(img.shape[2:], predictions[0])
    return mask

def polygons_to_geojson(building_polygons: list[Polygon], water_polygons: list[Polygon]):
    geojson = {
        'type': 'FeatureCollection',
        'features': []
    }

    for polygon in building_polygons:
        geojson['features'].append({
            'type': 'Feature',
            'geometry': shapely.geometry.mapping(polygon),
            'properties': {
                'type': 'building'
            }
        })

    for polygon in water_polygons:
        geojson['features'].append({
            'type': 'Feature',
            'geometry': shapely.geometry.mapping(polygon),
            'properties': {
                'type': 'water'
            }
        })

    return geojson

if __name__ == "__main__":
    model_path = sys.argv[1]
    chips_dir = sys.argv[2]
    coord_lookup_table_path = sys.argv[3]
    
    model = tf.keras.models.load_model(model_path, compile=False)
    coord_lookup_table = read_coord_lookup_table(coord_lookup_table_path)    
    building_polygons, water_polygons = chips_to_polygons(model, chips_dir, coord_lookup_table)
    geojson = polygons_to_geojson(building_polygons, water_polygons)
    with open('output.geojson', 'w') as f:
        json.dump(geojson, f)

