"""
container_body PNG 후처리 (초록 크로마키 배경 버전)
- 초록(#00ff00) 크로마키 제거
- 외곽 투명 여백 crop
- RGB 48-color quantize + alpha threshold
- optimize + max compression
"""
import os
import numpy as np
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
SRC = os.path.join(ROOT, 'versions/container_raw_v1/container.png')
DST = os.path.join(ROOT, 'skins/neon/container/container_body.png')

img = Image.open(SRC).convert('RGBA')
print(f'src: {img.size}, {os.path.getsize(SRC)/1024:.1f}KB')

# Gemini 워터마크 제거 — 우하단 코너 200x200
arr = np.array(img)
h, w = arr.shape[:2]
arr[h-200:h, w-200:w, 3] = 0
img = Image.fromarray(arr, 'RGBA')
print('watermark corner cleared')

# 초록 크로마키 제거
arr = np.array(img)
mask = (arr[:, :, 1] > 150) & (arr[:, :, 0] < 120) & (arr[:, :, 2] < 120)
arr[mask, 3] = 0
# edge desaturation: 남은 초록 fringe 억제
edge = ~mask & (arr[:, :, 1] > arr[:, :, 0]) & (arr[:, :, 1] > arr[:, :, 2])
arr[edge, 1] = np.minimum(arr[edge, 0], arr[edge, 2])
img = Image.fromarray(arr, 'RGBA')
print(f'chroma removed')

bbox = img.getbbox()
if bbox:
    img = img.crop(bbox)
    print(f'cropped: {img.size}')

# 다운샘플링
TARGET_W = 400
aspect = img.size[1] / img.size[0]
target_h = int(TARGET_W * aspect)
img = img.resize((TARGET_W, target_h), Image.LANCZOS)
print(f'resized: {img.size}')

arr = np.array(img)
a = arr[:, :, 3].astype(np.int32)
a_new = np.where(a < 60, 0, a)
mask_mid = (a_new >= 60) & (a_new < 180)
a_new[mask_mid] = ((a_new[mask_mid] - 60) * 255 // 120).clip(0, 255)
arr[:, :, 3] = a_new.astype(np.uint8)
img = Image.fromarray(arr, 'RGBA')

r, g, b, a = img.split()
rgb = Image.merge('RGB', (r, g, b))
p = rgb.quantize(colors=48, method=2)
rgb_q = p.convert('RGB')
final = Image.merge('RGBA', (*rgb_q.split(), a))

final.save(DST, optimize=True, compress_level=9)
print(f'dst: {final.size}, {os.path.getsize(DST)/1024:.1f}KB')
