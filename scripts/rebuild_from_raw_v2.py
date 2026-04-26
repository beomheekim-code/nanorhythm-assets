"""
sakura_tree 재처리 — 최소 처리.
- left: raw + 녹색/워터마크 제거 + 800px 다운스케일. stretch 제거.
- right: user-edit 백업 + 800px 다운스케일.

stretch 제거 (이전 1.8x trunk stretch 가 trunk 끝 부분 늘려서 어색하다는 보고).
canopy + trunk 모두 raw 비율 그대로.
"""
import os
import shutil
import numpy as np
from PIL import Image

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
CONTAINER = os.path.join(ROOT, 'skins', 'neon', 'container')
RAW = os.path.join(CONTAINER, 'Gemini_Generated_Image_sessbksessbksess.png')
DST_L = os.path.join(CONTAINER, 'sakura_tree_left.png')
DST_R = os.path.join(CONTAINER, 'sakura_tree_right.png')
RIGHT_BACKUP = os.path.join(ROOT, 'versions', 'sakura_tree_pre_holefill_v2', 'sakura_tree_right.png')

TARGET_W = 800

# === LEFT: raw 처리 ===
img = Image.open(RAW).convert('RGBA')
arr = np.array(img)
h, w = arr.shape[:2]
print(f'raw: {w}x{h}')

# Green chroma — loose 조건 (g 가 다른 채널보다 명확히 우세 = 모든 초록 잡음, 이끼 잔존 방지)
r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
green = (g.astype(int) > r.astype(int) + 15) & (g.astype(int) > b.astype(int) + 15) & (g > 80)
arr[green, 3] = 0
print(f'  green (loose): {int(green.sum())}')

# Watermark — 우하단 250x250 영역에서 회색 픽셀만 (trunk brown 은 RGB 차이 커서 보존)
WM_BOX = 250
ry, rx = arr[h-WM_BOX:h, w-WM_BOX:w, 0], arr[h-WM_BOX:h, w-WM_BOX:w, 1]
rb = arr[h-WM_BOX:h, w-WM_BOX:w, 2]
gray = (np.abs(ry.astype(int) - rx.astype(int)) < 30) & (np.abs(rx.astype(int) - rb.astype(int)) < 30) & (ry > 100)
arr[h-WM_BOX:h, w-WM_BOX:w, 3][gray] = 0
print(f'  watermark gray pixels: {int(gray.sum())}')

img = Image.fromarray(arr, 'RGBA')

# bbox crop
img = img.crop(img.getbbox())
W, H = img.size
print(f'  bbox: {W}x{H}')

# 다운스케일 (800px 폭)
scale = TARGET_W / W
img = img.resize((TARGET_W, int(H * scale)), Image.LANCZOS)
img.save(DST_L, optimize=True, compress_level=9)
print(f'left: {img.size}, {os.path.getsize(DST_L)/1024:.0f} KB')

# === RIGHT: user-edit backup + 다운스케일 ===
right_img = Image.open(RIGHT_BACKUP).convert('RGBA')
RW, RH = right_img.size
right_img = right_img.resize((TARGET_W, int(RH * (TARGET_W / RW))), Image.LANCZOS)
right_img.save(DST_R, optimize=True, compress_level=9)
print(f'right: {right_img.size} (user-edit + 다운스케일), {os.path.getsize(DST_R)/1024:.0f} KB')
