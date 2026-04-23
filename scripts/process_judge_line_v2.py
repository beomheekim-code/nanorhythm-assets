"""
판정선 에셋 3종 후처리 (초록 크로마키 배경 버전)
Usage: python process_judge_line_v2.py <bar|deco_left|deco_right>

- 크로마키 제거
- Gemini 워터마크 제거 (우하단 200x200)
- bbox crop (빈 공간 제거)
- 리사이즈 (바 = 2048폭, 데코 = 512x512)
- 백업은 versions/judge_line_v2_raw/ 에 저장
"""
import os
import sys
import shutil
import numpy as np
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)

variant = sys.argv[1] if len(sys.argv) > 1 else 'bar'
fname = f'judge_line_{variant}.png'
SRC = os.path.join(ROOT, f'skins/neon/judge_line/{fname}')
DST = SRC  # 덮어쓰기
BACKUP_DIR = os.path.join(ROOT, 'versions/judge_line_v2_raw')
os.makedirs(BACKUP_DIR, exist_ok=True)
BACKUP = os.path.join(BACKUP_DIR, fname)

# 원본 백업 (최초 1회만)
if not os.path.exists(BACKUP):
    shutil.copy(SRC, BACKUP)
    print(f'backup: {BACKUP}')

img = Image.open(BACKUP).convert('RGBA')  # raw 는 항상 backup 에서 읽기
print(f'src: {img.size}, {os.path.getsize(BACKUP)/1024:.1f}KB')

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

# bbox crop (빈 공간 제거)
bbox = img.getbbox()
if bbox:
    img = img.crop(bbox)
    print(f'cropped: {img.size}')

# 리사이즈
if variant == 'bar':
    # 바 — 가로 2048px, 세로는 자연비율 (얇은 선 유지)
    TARGET_W = 2048
    aspect = img.size[1] / img.size[0]
    img = img.resize((TARGET_W, int(TARGET_W * aspect)), Image.LANCZOS)
else:
    # 데코 — 정사각 512x512 (자연비율 유지한 채로 패딩 없이 fit)
    # 이미 정사각 이미지라 비율 유지
    TARGET = 512
    # 현재 비율 유지 — max 변 기준 512
    scale = TARGET / max(img.size)
    nw = int(img.size[0] * scale)
    nh = int(img.size[1] * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
print(f'resized: {img.size}')

# 알파 threshold (깔끔한 엣지)
arr = np.array(img)
a = arr[:, :, 3].astype(np.int32)
a_new = np.where(a < 40, 0, a)
arr[:, :, 3] = a_new.astype(np.uint8)
img = Image.fromarray(arr, 'RGBA')

# 48-color quantize + compress
r, g, b, a = img.split()
rgb = Image.merge('RGB', (r, g, b))
p = rgb.quantize(colors=48, method=2)
rgb_q = p.convert('RGB')
final = Image.merge('RGBA', (*rgb_q.split(), a))

final.save(DST, optimize=True, compress_level=9)
print(f'dst: {final.size}, {os.path.getsize(DST)/1024:.1f}KB')
