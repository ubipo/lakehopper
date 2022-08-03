import numpy as np


LABEL_COLORS = {
    'building': (227,  26, 28),
    'water':    ( 30,  95, 170),
    'ground':   (  0,   0,   0),
}

def colorize_byte_mask(mask: np.ndarray) -> np.ndarray:
    """
    Convert a byte mask to a color mask.
    """
    color_mask = np.zeros(mask.shape[:2] + (3,), dtype=np.uint8)
    for byte, (_label, color) in enumerate(LABEL_COLORS.items()):
        locs = np.where((mask[:, :] == byte))
        color_mask[locs[0], locs[1]] = color
    return color_mask
