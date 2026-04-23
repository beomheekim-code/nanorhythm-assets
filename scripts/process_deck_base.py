"""
deck_base PNG 후처리 — sakura_ui 점수 패널 배경.
- 초록 크로마키 제거
- Gemini 워터마크 + 엣지 artifact 제거
- bbox crop
- 리사이즈 (1024px 폭, 매 프레임 drawImage 비용 절감)
- 48 color quantize + max compress
"""
import os
import shutil
import numpy as np
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
DST = os.path.join(ROOT, 'skins/neon/backplate/deck_base.png')
BACKUP_DIR = os.path.join(ROOT, 'versions/deck_base_raw_v1')
os.makedirs(BACKUP_DIR, exist_ok=True)
BACKUP = os.path.join(BACKUP_DIR, 'deck_base.png')

# 최초 1회 백업
if not os.path.exists(BACKUP):
    shutil.copy(DST, BACKUP)
    print(f'backup: {BACKUP}')

img = Image.open(BACKUP).convert('RGBA')
print(f'src: {img.size}, {os.path.getsize(BACKUP)/1024:.1f}KB')

# Gemini 워터마크 + 엣지 artifact 제거
arr = np.array(img)
h, w = arr.shape[:2]
arr[h-200:h, w-200:w, 3] = 0  # 우하단 워터마크
arr[0:5, :, 3] = 0
arr[h-5:h, :, 3] = 0
arr[:, 0:5, 3] = 0
arr[:, w-5:w, 3] = 0
img = Image.fromarray(arr, 'RGBA')
print('watermark + edges cleared')

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

# 리사이즈 — 1024px 폭으로
TARGET_W = 1024
aspect = img.size[1] / img.size[0]
img = img.resize((TARGET_W, int(TARGET_W * aspect)), Image.LANCZOS)
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
