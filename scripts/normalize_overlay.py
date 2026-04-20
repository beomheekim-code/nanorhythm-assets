# -*- coding: utf-8 -*-
"""
오버레이 각 셀의 flower 크기/위치를 통일.
각 셀에서 flower tight bbox 추출 → 목표 크기로 리사이즈 → 일관된 위치에 재배치.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image
import numpy as np

PATH = 'D:/리듬게임/skins/neon/note/벚꽃_노트키_오버레이.png'
COLS, ROWS = 4, 2
CELL_W, CELL_H = 688, 768

# 목표: 꽃을 셀 폭의 55% 로 통일, 셀 상단 10% 위치에 배치
TARGET_W_RATIO = 0.55
TOP_OFFSET_RATIO = 0.08

im = Image.open(PATH).convert('RGBA')
a = np.array(im)
alpha = a[:, :, 3]

new_canvas = np.zeros_like(a)

for row in range(ROWS):
    for col in range(COLS):
        x0, y0 = col * CELL_W, row * CELL_H
        x1, y1 = x0 + CELL_W, y0 + CELL_H
        cell_alpha = alpha[y0:y1, x0:x1]
        mask = cell_alpha > 0
        if mask.sum() == 0:
            continue
        ys, xs = np.where(mask)
        bx, by = xs.min(), ys.min()
        bw = xs.max() - xs.min() + 1
        bh = ys.max() - ys.min() + 1
        # crop flower
        flower = a[y0 + by: y0 + by + bh, x0 + bx: x0 + bx + bw]
        flower_pil = Image.fromarray(flower)
        # 목표 크기 (aspect 유지)
        target_w = int(CELL_W * TARGET_W_RATIO)
        target_h = int(target_w * bh / bw)
        flower_resized = flower_pil.resize((target_w, target_h), Image.LANCZOS)
        # 셀 내 paste 위치 (상단 중앙)
        paste_x = x0 + (CELL_W - target_w) // 2
        paste_y = y0 + int(CELL_H * TOP_OFFSET_RATIO)
        # numpy 배열로 pasting
        fx = np.array(flower_resized)
        # alpha 블렌드
        fa = fx[:, :, 3:4].astype(float) / 255.0
        new_canvas[paste_y:paste_y + target_h, paste_x:paste_x + target_w, :3] = (
            fx[:, :, :3] * fa + new_canvas[paste_y:paste_y + target_h, paste_x:paste_x + target_w, :3] * (1 - fa)
        ).astype(np.uint8)
        new_canvas[paste_y:paste_y + target_h, paste_x:paste_x + target_w, 3] = np.maximum(
            new_canvas[paste_y:paste_y + target_h, paste_x:paste_x + target_w, 3],
            fx[:, :, 3]
        )
        print(f'cell [{row},{col}] flower bbox {bw}x{bh} → {target_w}x{target_h} at ({paste_x},{paste_y})')

Image.fromarray(new_canvas).save(PATH)
print(f'\n✓ normalized {PATH}')
