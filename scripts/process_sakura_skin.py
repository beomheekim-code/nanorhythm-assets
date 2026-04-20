# -*- coding: utf-8 -*-
"""
벚꽃 스킨 3개 스트립 (벚꽃_노트 / 홀드머리 / 홀드몸통) 처리:
1. 어두운 바깥 배경을 투명으로 (max(R,G,B) < 35 → alpha=0)
2. 가로 8등분 후 각 셀의 non-transparent 타이트 bbox 산출
3. 원본 파일에 투명화된 결과 덮어쓰기
4. SKINS config 에 넣을 좌표 출력
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image
import numpy as np

BASE = 'D:/리듬게임/skins/neon/note'
FILES = ['벚꽃_노트.png', '벚꽃_홀드머리.png', '벚꽃_홀드몸통.png']

def process(name):
    path = os.path.join(BASE, name)
    im = Image.open(path).convert('RGBA')
    a = np.array(im)
    H, W = a.shape[:2]

    # 1. 배경 투명화 — 어두운 픽셀 (모든 채널 < 35)
    rgb = a[:, :, :3]
    max_ch = rgb.max(axis=2)
    dark_mask = max_ch < 35
    a[dark_mask, 3] = 0

    # 2. 가로 8등분 → 각 셀에서 non-transparent bbox
    cell_w = W / 8.0
    alpha = a[:, :, 3]
    cells = []
    for i in range(8):
        x0 = int(round(i * cell_w))
        x1 = int(round((i + 1) * cell_w))
        slab = alpha[:, x0:x1]
        cols_has = slab.max(axis=0) > 0
        rows_has = slab.max(axis=1) > 0
        cx = np.where(cols_has)[0]
        ry = np.where(rows_has)[0]
        if len(cx) == 0 or len(ry) == 0:
            cells.append(None)
            continue
        cs = x0 + cx[0]
        ce = x0 + cx[-1]
        rs = ry[0]
        re_ = ry[-1]
        cells.append((int(cs), int(rs), int(ce - cs + 1), int(re_ - rs + 1)))

    # 3. 저장
    Image.fromarray(a).save(path)
    return cells, (W, H)

print('=== 벚꽃 스킨 처리 결과 ===\n')
for name in FILES:
    cells, size = process(name)
    print(f'{name}  size={size}')
    for i, c in enumerate(cells):
        print(f'  [{i}] {c}')
    print()
