from typing import Mapping, Union
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf


# https://stackoverflow.com/a/312464/7120579
def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def show_two(title1, img1, title2, img2):
    plt.figure(figsize=(11,8), dpi=100)
    plt.subplot(1,2,1)
    plt.title(title1)
    plt.imshow(img1)

    plt.subplot(1,2,2)
    plt.title(title2)
    plt.imshow(img2)

IMAGE_TITLES = ['Image', 'True Label Mask', 'Predicted Label Mask']
ImgMask = Union[tuple[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray, np.ndarray]]

def show(rows: Union[list[ImgMask], ImgMask]):
    if isinstance(rows, tuple):
        rows = [rows]
    plt.figure(figsize=(11,8), dpi=100)
    nbro_rows = len(rows)
    nbro_columns = max((len(r) for r in rows))
    if nbro_columns > len(IMAGE_TITLES):
        raise ValueError(f"Too many columns: {nbro_columns} > {len(IMAGE_TITLES)}")
    for y, row in enumerate(rows):
        for x, (image, title) in enumerate(zip(row, IMAGE_TITLES)):
            plt.subplot(nbro_rows, nbro_columns, y + x + 1)
            plt.title(title)
            if isinstance(image, tf.Tensor):
                print('Converting tensor to numpy array...')
                image = tf.keras.utils.array_to_img(image)
            plt.imshow(image, interpolation='none', aspect='equal')
            plt.axis('off')

# def show(image_rows: list[tuple[np.ndarray, np.ndarray] | tuple[np.ndarray, np.ndarray, np.ndarray]]):
#     plt.figure(figsize=(11,8), dpi=100)
#     rows = list(chunks(list(images.items()), 3))
#     nmbro_rows = len(rows)
#     max_row_length = max((len(r) for r in rows))

#     for y, row in enumerate(rows):
#         for x, (name, image) in enumerate(row):
#             plt.subplot(nmbro_rows, max_row_length, y + x + 1)
#             plt.title(name)
#             plt.imshow(image)

def show_rows(columns: Mapping[str, list[np.ndarray]]):
    plt.figure(figsize=(11,8), dpi=100)
    nmbro_columns = len(columns)
    max_column_length = max((len(c) for c in columns.values()))
    f, axarr = plt.subplots(max_column_length, nmbro_columns)

    for y, (name, column) in enumerate(columns.items()):
        for x, image in enumerate(column):
            axarr[x, y].subplot(max_column_length, nmbro_columns)
            if y == 0:
                axarr[x, y].title(name)
            axarr[x, y].imshow(image)

# def dataset_to_numpy(dataset, n):
#     return next(iter(visualisation_dataset))
