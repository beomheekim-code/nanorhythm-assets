"""
container_body PNG 후처리
- 외곽 투명 여백 crop
- ★ 체커 잔흔 제거 — alpha threshold 강화 (Gemini 투명배경 PNG 의 체커 fringe 제거)
- RGB 64-color quantize (alpha 는 threshold 처리 — soft glow 일부 보존)
- optimize + max compression

★ 차후 초록 크로마키 배경으로 받은 PNG 는 이 스크립트 복사 후 크로마키 제거 추가.
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

bbox = img.getbbox()
if bbox:
    img = img.crop(bbox)
    print(f'cropped: {img.size}')

# 다운샘플링 — 실제 렌더 크기 대비 2x retina 면 충분
TARGET_W = 400
aspect = img.size[1] / img.size[0]
target_h = int(TARGET_W * aspect)
img = img.resize((TARGET_W, target_h), Image.LANCZOS)
print(f'resized: {img.size}')

# ★ alpha threshold — 체커 fringe 제거
#    alpha < 90: 완전 투명 / 90~200: 리매핑(0~255) / 200+: 유지
arr = np.array(img)
a = arr[:, :, 3].astype(np.int32)
a_new = np.where(a < 90, 0, a)
mask_mid = (a_new >= 90) & (a_new < 200)
a_new[mask_mid] = ((a_new[mask_mid] - 90) * 255 // 110).clip(0, 255)
arr[:, :, 3] = a_new.astype(np.uint8)
img = Image.fromarray(arr, 'RGBA')

r, g, b, a = img.split()
rgb = Image.merge('RGB', (r, g, b))
p = rgb.quantize(colors=48, method=2)
rgb_q = p.convert('RGB')
final = Image.merge('RGBA', (*rgb_q.split(), a))

final.save(DST, optimize=True, compress_level=9)
print(f'dst: {final.size}, {os.path.getsize(DST)/1024:.1f}KB')
