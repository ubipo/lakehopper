from dataclasses import replace
from pathlib import Path
import cv2
import os
import numpy as np

from config import LABELMAP, INV_LABELMAP

size   = 300
stride = 300

def color2class(orthochip, img):
    ret = np.zeros((img.shape[0], img.shape[1]), dtype='uint8')
    ret = np.dstack([ret, ret, ret])
    colors = np.unique(img.reshape(-1, img.shape[2]), axis=0)

    # Skip any chips that would contain magenta (IGNORE) pixels
    seen_colors = set( [tuple(color) for color in colors] )
    IGNORE_COLOR = LABELMAP[0]
    if IGNORE_COLOR in seen_colors:
        return None, None

    for color in colors:
        locs = np.where( (img[:, :, 0] == color[0]) & (img[:, :, 1] == color[1]) & (img[:, :, 2] == color[2]) )
        ret[ locs[0], locs[1], : ] = INV_LABELMAP[ tuple(color) ] - 1

    return orthochip, ret

def image2tile(prefix, scene, image_path, label_mask_path, windowx=size, windowy=size, stridex=stride, stridey=stride):

    ortho = cv2.imread(str(image_path))
    label = cv2.imread(str(label_mask_path))

    assert(ortho.shape[0] == label.shape[0])
    assert(ortho.shape[1] == label.shape[1])

    shape = ortho.shape

    xsize = shape[1]
    ysize = shape[0]
    print(f"converting image {image_path} {xsize}x{ysize} to chips ...")

    counter = 0

    for xi in range(0, shape[1] - windowx, stridex):
        for yi in range(0, shape[0] - windowy, stridey):

            orthochip = ortho[yi:yi+windowy, xi:xi+windowx, :]
            labelchip = label[yi:yi+windowy, xi:xi+windowx, :]

            orthochip, classchip = color2class(orthochip, labelchip)

            if classchip is None:
                continue

            orthochip_filename = os.path.join(prefix, 'image-chips', scene + '-' + str(counter).zfill(6) + '.png')
            labelchip_filename = os.path.join(prefix, 'label-chips', scene + '-' + str(counter).zfill(6) + '.png')

            cv2.imwrite(orthochip_filename, orthochip)
            cv2.imwrite(labelchip_filename, classchip)
            counter += 1


