import itertools
from pathlib import Path
from typing import Callable, Iterable
import fiona
import argparse
import cv2
import glymur
from glymur import jp2box
from osgeo import gdal
from shapely.geometry import MultiPolygon, Polygon
import shapely.ops
import numpy as np
from .colormaps import IV_ORTHO_BG_COLOR, IV_ORTHO_MID_LABEL_COLOR_MAP

CATEGORY_CODE_LABEL_MAP = {
    "Gba": "building",
    "Gbg": "building",
    # 'gr' for 'Grachten'. Nearly never applicable (dried up, too shallow). And
    # if an instance _is_ applicable, it usually needs to be manually corrected
    # anyway.
    # 'Wgr': 'water',
    "Wtz": "water",
}

# Number of chunks to divide the orthophoto/geometries into
NBRO_CHUNKS = (12, 8)


def pixel_to_geo_coord(geo_transform, pixel_coord):
    """Transform pixel to geographic coordinates.
    See:
    https://gdal.org/api/gdaldataset_cpp.html#_CPPv4N11GDALDataset15GetGeoTransformEPd
    https://gdal.org/tutorials/geotransforms_tut.html
    """
    pixel_x, pixel_y = pixel_coord
    a, b, c, d, e, f = geo_transform
    assert c == 0  # row rotation, too difficult to deal with
    assert e == 0  # column rotation
    return (a + b * pixel_x + c * pixel_y, d + e * pixel_x + f * pixel_y)


def geo_to_pixel_coord(geo_transform, geo_coord):
    """Transform geographic to pixel coordinates."""
    geo_x, geo_y = geo_coord
    a, b, c, d, e, f = geo_transform
    determinant_inv = 1 / (b * f - c * e)
    return (
        int(determinant_inv * (+f * (geo_x - a) - c * (geo_y - d))),
        int(determinant_inv * (-e * (geo_x - a) + b * (geo_y - d))),
    )


def jp2_to_gtif(jp2: glymur.Jp2k):
    gtif_data = next(
        box
        for box in jp2.box
        if isinstance(box, jp2box.UUIDBox) and box.uuid == jp2box._GEOTIFF_UUID
    )
    in_mem_name = "/vsimem/geo.tif"
    gdal.FileFromMemBuffer(in_mem_name, gtif_data.raw_data)
    gtif = gdal.Open(in_mem_name)
    assert gtif.RasterXSize == 1 and gtif.RasterYSize == 1
    return gtif


def polygon_to_ring_list(polygon: Polygon, transform: Callable = lambda c: c):
    return [
        [transform(coord) for coord in ring.coords]
        for ring in (polygon.exterior, *polygon.interiors)
    ]


def multipolygon_to_fiona_record(multi_polygon: MultiPolygon):
    multipolygon_coordinates = [
        polygon_to_ring_list(polygon) for polygon in multi_polygon.geoms
    ]
    fiona_record = {
        "geometry": {"coordinates": multipolygon_coordinates, "type": "MultiPolygon"}
    }
    return fiona_record


def write_to_gpkg():
    meta = {
        "schema": {"geometry": "MultiPolygon"},
        "crs": in_crs,
        "crs_wky": in_crs_wkt,
    }
    with fiona.open("out.gpkg", "w", **meta, driver="GPKG") as gpkg_file:
        gpkg_file.write(fiona_record)


def polygon_to_coco_annotation(
    polygon: Polygon, annotation_id: int, category_id: int, image_id: int
):
    segmentation = np.array(polygon.exterior.coords).ravel().tolist()
    min_x, min_y, max_x, max_y = polygon.bounds
    width = max_x - min_x
    height = max_y - min_y
    bbox = (min_x, min_y, width, height)
    return {
        "segmentation": segmentation,
        "area": polygon.area,
        "iscrowd": 0,
        "image_id": image_id,
        "bbox": bbox,
        "category_id": category_id,
        "id": annotation_id,
    }


def labels_to_coco_categories(labels: Iterable[str]):
    return [
        {"id": i, "name": label, "supercategory": "none"}
        for i, label in enumerate(labels)
    ]


def chunk_iv_ortho_mid(base_path: Path, map_sheet_code: Path):
    orthophoto_path = base_path / f"OMWRGBMRVL_K{map_sheet_code}.jp2"
    print(f"Processing map sheet {map_sheet_code}...")
    grb_zip_paths = base_path.glob(f"*_{map_sheet_code}_Shapefile.zip")
    category_zip_paths = {}
    for grb_zip_path in grb_zip_paths:
        category_code = grb_zip_path.stem[: grb_zip_path.stem.index("_")]
        if category_code in CATEGORY_CODE_LABEL_MAP.keys():
            category_zip_paths[category_code] = grb_zip_path

    missing_codes = set(CATEGORY_CODE_LABEL_MAP.keys()).difference(
        category_zip_paths.keys()
    )
    if missing_codes != set():
        print(f"Missing category codes: {missing_codes}")

    label_polygons_map = {}
    for category_code, grb_zip_path in category_zip_paths.items():
        vfs_path = (
            f"zip://{grb_zip_path}!/Shapefile/{category_code}{map_sheet_code}.shp"
        )
        with fiona.open(vfs_path, "r") as shp_file:
            label = CATEGORY_CODE_LABEL_MAP[category_code]
            polygons = label_polygons_map.get(label, [])
            label_polygons_map[label] = polygons
            for shape in shp_file:
                rings = shape["geometry"]["coordinates"]
                outer = rings[0]
                inners = rings[1:]
                if len(outer) < 3:
                    continue
                polygons.append(Polygon(outer, inners))

    jp2 = glymur.Jp2k(orthophoto_path)
    gtif = jp2_to_gtif(jp2)
    geo_transform = gtif.GetGeoTransform(can_return_null=True)
    nbro_chunks_x, nbro_chunks_y = NBRO_CHUNKS
    ortho_h, ortho_w, _c = jp2.shape
    chunk_ortho_w = int(ortho_w / nbro_chunks_x)
    chunk_ortho_h = int(ortho_h / nbro_chunks_y)

    chunks_path = orthophoto_path.parent / "chunks"
    ortho_chunks_path = chunks_path / "ortho"
    ortho_chunks_path.mkdir(exist_ok=True, parents=True)
    mask_chunks_path = chunks_path / "mask"
    mask_chunks_path.mkdir(exist_ok=True, parents=True)

    ortho = cv2.imread(str(orthophoto_path))

    for chunk_y, chunk_x in itertools.product(
        range(nbro_chunks_y), range(nbro_chunks_x)
    ):
        print(f"Processing chunk {(chunk_x, chunk_y)}...")

        ortho_x_min = chunk_x * chunk_ortho_w
        ortho_y_min = chunk_y * chunk_ortho_h
        ortho_x_max = ortho_x_min + chunk_ortho_w
        ortho_y_max = ortho_y_min + chunk_ortho_h
        # geo_y_min and geo_y_max are mirrored horizontally because pixel
        # coordinates start from the top left, while geographic coordinates
        # start bottom left
        (geo_x_min, geo_y_max) = pixel_to_geo_coord(
            geo_transform, (ortho_x_min, ortho_y_min)
        )
        (geo_x_max, geo_y_min) = pixel_to_geo_coord(
            geo_transform, (ortho_x_max, ortho_y_max)
        )

        def geo_to_chunk_pixel_coord(c):
            (pixel_x, pixel_y) = geo_to_pixel_coord(geo_transform, c)
            return pixel_x - ortho_x_min, pixel_y - ortho_y_min

        ground_color = IV_ORTHO_BG_COLOR
        chunk_mask = np.tile(
            np.array(ground_color, dtype="uint8"), (chunk_ortho_h, chunk_ortho_w, 1)
        )

        for label, polygons in label_polygons_map.items():
            color = IV_ORTHO_MID_LABEL_COLOR_MAP[label]
            multi_polygon = MultiPolygon(polygons)
            clipped = shapely.ops.clip_by_rect(
                MultiPolygon(multi_polygon), geo_x_min, geo_y_min, geo_x_max, geo_y_max
            )
            if clipped.is_empty:
                continue

            if isinstance(clipped, Polygon):
                clipped_polygons = [clipped]
            elif isinstance(clipped, MultiPolygon):
                clipped_polygons = clipped.geoms
            else:
                raise RuntimeError(
                    f"Unexpected clipped geometry type: {clipped.__class__}"
                )

            for polygon in clipped_polygons:
                rings = polygon_to_ring_list(polygon, geo_to_chunk_pixel_coord)
                # See: https://forum.opencv.org/t/fillpolygon-api-usage/3899/2
                rings_shaped = [np.array(ring).reshape((-1, 1, 2)) for ring in rings]
                cv2.fillPoly(chunk_mask, rings_shaped, color, cv2.LINE_8)
                # raise err

        chunk_ortho = ortho[ortho_y_min:ortho_y_max, ortho_x_min:ortho_x_max]
        name = f"{map_sheet_code}-{chunk_x:03}-{chunk_y:03}.png"
        cv2.imwrite(str(ortho_chunks_path / name), chunk_ortho)
        cv2.imwrite(str(mask_chunks_path / name), chunk_mask)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("iv-ortho-mid-preprocess")
    parser.add_argument("MAP_SHEET_CODE", type=Path, help="NGI 1/16 map sheet code")
    parser.add_argument(
        "BASE_PATH",
        type=Path,
        help="Path to directory containing jp2 file and GBG zips",
    )
    args = parser.parse_args()

    # with open('/data/projects/lakehopper/segmentation/datasets/iv-ortho-mid/218z/Wtz_20220704_218z_Shapefile/Shapefile/Wtz218z.shp', 'br') as f:
    #     # ioa = io.BytesIO(bytesaa)
    #     # print(fiona.drvsupport.supported_drivers.keys())
    #     file_buffered = io.BytesIO(f.read())

    # with fiona.open('/data/projects/lakehopper/segmentation/datasets/iv-ortho-mid/218z/Wtz_20220704_218z_Shapefile/Shapefile/Wtz218z.shp', 'r') as shp:
    #     print(shp.meta)

    chunk_iv_ortho_mid(args.BASE_PATH, args.MAP_SHEET_CODE)
