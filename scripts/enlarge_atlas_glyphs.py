"""
numbers_atlas 글자 크기 키우기.
- 비율 유지 (글자 모양 보존)
- cell 폭 확장 (1024x572 → 1800x572 = cellW 85 → 150)
- 각 글자 height 92% 차지 (526px)
"""
import os
import numpy as np
from PIL import Image

P = r'D:\nanorhythm-assets\nanorhythm-assets\skins\neon\numbers\numbers_atlas.png'
N_CELLS = 12
NEW_CELL_W = 150  # 85 → 150 (글자 더 크게 fit)

img = Image.open(P).convert('RGBA')
W, H = img.size
old_cellW = W // N_CELLS
print(f'atlas: {W}x{H}, old cellW {old_cellW}')

new_W = N_CELLS * NEW_CELL_W
new_arr = np.zeros((H, new_W, 4), dtype=np.uint8)

for i in range(N_CELLS):
    cell = img.crop((i*old_cellW, 0, (i+1)*old_cellW, H))
    cell_bbox = cell.getbbox()
    if not cell_bbox:
        continue
    glyph = cell.crop(cell_bbox)
    gw, gh = glyph.size
    # 비율 무시 stretch — 모든 글자 동일 size (일관성 우선)
    target_h = int(H * 0.92)
    new_w = int(NEW_CELL_W * 0.92)
    glyph_r = glyph.resize((new_w, target_h), Image.LANCZOS)
    px = i*NEW_CELL_W + (NEW_CELL_W - new_w) // 2
    py = (H - target_h) // 2
    new_arr[py:py+target_h, px:px+new_w] = np.array(glyph_r)
    print(f'  cell {i}: glyph {gw}x{gh} → {new_w}x{target_h}')

Image.fromarray(new_arr, 'RGBA').save(P, optimize=True, compress_level=9)
print(f'saved: {new_W}x{H}, {os.path.getsize(P)/1024:.0f} KB')
