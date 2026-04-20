# -*- coding: utf-8 -*-
"""
노트키 오버레이의 baked-in 체크/회색 배경 제거.
각 셀 코너에서 flood fill (저채도 픽셀만) → 회색 bg 만 투명화, 꽃 보존.
"""
import sys, io, os
from collections import deque
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image
import numpy as np

PATH = 'D:/리듬게임/skins/neon/note/벚꽃_노트키_오버레이.png'
SAT_THRESH = 25  # max-min < 이 값이면 저채도(회색) → bg 후보
CELL_W, CELL_H = 688, 768
COLS, ROWS = 4, 2

im = Image.open(PATH).convert('RGBA')
a = np.array(im)
H, W = a.shape[:2]
rgb = a[:, :, :3].astype(np.int16)
sat = rgb.max(axis=2) - rgb.min(axis=2)  # 0~255
low_sat = sat < SAT_THRESH  # gray 후보

# 각 셀 4 코너에서 flood fill
to_transparent = np.zeros((H, W), dtype=bool)
for row in range(ROWS):
    for col in range(COLS):
        x0 = col * CELL_W
        y0 = row * CELL_H
        x1 = x0 + CELL_W - 1
        y1 = y0 + CELL_H - 1
        corners = [(x0, y0), (x1, y0), (x0, y1), (x1, y1)]
        for (cx, cy) in corners:
            if not low_sat[cy, cx] or to_transparent[cy, cx]:
                continue
            q = deque([(cx, cy)])
            to_transparent[cy, cx] = True
            while q:
                x, y = q.popleft()
                for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx, ny = x+dx, y+dy
                    if x0 <= nx <= x1 and y0 <= ny <= y1:
                        if low_sat[ny, nx] and not to_transparent[ny, nx]:
                            to_transparent[ny, nx] = True
                            q.append((nx, ny))

a[to_transparent, 3] = 0
Image.fromarray(a).save(PATH)
print(f'cleared {to_transparent.sum()} / {H*W} ({to_transparent.sum()/(H*W)*100:.1f}%)')
