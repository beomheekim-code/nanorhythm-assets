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
WM = 100  # 워터마크 박스 (50 은 너무 작아서 일부 잔존했음)

# === LEFT: raw 처리 ===
img = Image.open(RAW).convert('RGBA')
arr = np.array(img)
h, w = arr.shape[:2]
print(f'raw: {w}x{h}')

# Green chroma
r, g, b = arr[:,:,0], arr[:,:,1], arr[:,:,2]
green = (g > 150) & (r < 120) & (b < 120)
arr[green, 3] = 0

# Watermark 우하단 50x50 만
arr[h-WM:h, w-WM:w, 3] = 0

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
