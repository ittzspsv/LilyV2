import numpy as np
from PIL import Image

def build_fade_mask(width, height, fade_start_x, fade_end_x, diagonal_shift: int = 80):
    arr = np.zeros((height, width), dtype=np.uint8)
    band_width = max(fade_end_x - fade_start_x, 1)
 
    for y in range(height):
        t_y   = y / (height - 1)
        shift = int((t_y - 0.5) * 2 * diagonal_shift)
        start = fade_start_x + shift
        end   = fade_end_x   + shift
 
        for x in range(width):
            if x <= start:
                alpha = 255
            elif x >= end:
                alpha = 0
            else:
                t = (x - start) / band_width
                t = t * t * (3 - 2 * t)
                alpha = int(255 * (1 - t))
            arr[y, x] = alpha
 
    return Image.fromarray(arr, mode="L")