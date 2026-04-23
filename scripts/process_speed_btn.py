"""
speed_minus / speed_plus PNG 후처리 (초록 크로마키 배경 버전)
Usage: python process_speed_btn.py <minus|plus>
"""
import os
import sys
import numpy as np
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)

variant = sys.argv[1] if len(sys.argv) > 1 else 'minus'
SRC = os.path.join(ROOT, f'versions/speed_raw_v1/speed_{variant}.png')
DST = os.path.join(ROOT, f'skins/neon/speed/speed_{variant}.png')

img = Image.open(SRC).convert('RGBA')
print(f'src: {img.size}, {os.path.getsize(SRC)/1024:.1f}KB')

# 초록 크로마키 제거
arr = np.array(img)
mask = (arr[:, :, 1] > 150) & (arr[:, :, 0] < 120) & (arr[:, :, 2] < 120)
arr[mask, 3] = 0
edge = ~mask & (arr[:, :, 1] > arr[:, :, 0]) & (arr[:, :, 1] > arr[:, :, 2])
arr[edge, 1] = np.minimum(arr[edge, 0], arr[edge, 2])
img = Image.fromarray(arr, 'RGBA')
print('chroma removed')

bbox = img.getbbox()
if bbox:
    img = img.crop(bbox)
    print(f'cropped: {img.size}')

# 버튼은 정사각 유지, 200px (2x retina 충분)
TARGET = 200
img = img.resize((TARGET, TARGET), Image.LANCZOS)
print(f'resized: {img.size}')

arr = np.array(img)
a = arr[:, :, 3].astype(np.int32)
a_new = np.where(a < 40, 0, a)
arr[:, :, 3] = a_new.astype(np.uint8)
img = Image.fromarray(arr, 'RGBA')

r, g, b, a = img.split()
rgb = Image.merge('RGB', (r, g, b))
p = rgb.quantize(colors=48, method=2)
rgb_q = p.convert('RGB')
final = Image.merge('RGBA', (*rgb_q.split(), a))

final.save(DST, optimize=True, compress_level=9)
print(f'dst: {final.size}, {os.path.getsize(DST)/1024:.1f}KB')
