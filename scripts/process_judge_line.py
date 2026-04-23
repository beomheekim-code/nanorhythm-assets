"""
judge_line PNG 후처리 (초록 크로마키 배경 버전)
- Gemini 워터마크 제거 (우하단 200x200)
- 초록(#00ff00) 크로마키 제거
- 꽃 문양 등 내부 장식은 보존
- optimize + max compression
"""
import os
import numpy as np
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
SRC = os.path.join(ROOT, 'versions/judge_line_raw_v1/judge_line.png')
DST = os.path.join(ROOT, 'skins/neon/judge_line/judge_line.png')

img = Image.open(SRC).convert('RGBA')
print(f'src: {img.size}, {os.path.getsize(SRC)/1024:.1f}KB')

# Gemini 워터마크 제거 — 우하단 200x200
arr = np.array(img)
h, w = arr.shape[:2]
arr[h-200:h, w-200:w, 3] = 0
img = Image.fromarray(arr, 'RGBA')
print('watermark corner cleared')

# 초록 크로마키 제거
arr = np.array(img)
mask = (arr[:, :, 1] > 150) & (arr[:, :, 0] < 120) & (arr[:, :, 2] < 120)
arr[mask, 3] = 0
edge = ~mask & (arr[:, :, 1] > arr[:, :, 0]) & (arr[:, :, 1] > arr[:, :, 2])
arr[edge, 1] = np.minimum(arr[edge, 0], arr[edge, 2])
img = Image.fromarray(arr, 'RGBA')
print('chroma removed')

# 리사이즈 — 1024px 폭으로 (매 프레임 drawImage 부하 절감)
TARGET_W = 1024
aspect = img.size[1] / img.size[0]
img = img.resize((TARGET_W, int(TARGET_W * aspect)), Image.LANCZOS)
print(f'resized: {img.size}')

img.save(DST, optimize=True, compress_level=9)
print(f'dst: {img.size}, {os.path.getsize(DST)/1024:.1f}KB')
