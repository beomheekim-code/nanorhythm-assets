"""
container_body PNG 후처리
- 외곽 투명 여백 crop
- RGB 64-color quantize (alpha 는 원본 유지 — soft glow 보존)
- optimize + max compression
"""
import os
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPT_DIR)
SRC = os.path.join(ROOT, 'skins/neon/container/container.png')
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

r, g, b, a = img.split()
rgb = Image.merge('RGB', (r, g, b))
p = rgb.quantize(colors=48, method=2)
rgb_q = p.convert('RGB')
final = Image.merge('RGBA', (*rgb_q.split(), a))

final.save(DST, optimize=True, compress_level=9)
print(f'dst: {final.size}, {os.path.getsize(DST)/1024:.1f}KB')
