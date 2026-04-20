# -*- coding: utf-8 -*-
"""
_cells/key_overlay/ 의 8 개별 셀을 사용해 벚꽃_노트.png 재생성.
기존 _cells/key_overlay/01~08.png 는 꽃이 셀 상단에 있지만 노트용으론 중앙 필요.
→ 각 셀에서 꽃 tight bbox 찾아서 400×400 square 캔버스 중앙에 재배치.
결과: 3200×400 RGBA (8셀 × 400×400 각각).

홀드머리용도 동일 소스라 복사 → 벚꽃_홀드머리.png.
"""
import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image
import numpy as np

BASE = 'D:/리듬게임/skins/neon/note'
CELLS_DIR = os.path.join(BASE, '_cells', 'key_overlay')
OUT_NOTE = os.path.join(BASE, '벚꽃_노트.png')
OUT_HEAD = os.path.join(BASE, '벚꽃_홀드머리.png')

CELL_SIZE = 400   # 최종 셀당 크기 (정사각)
N_CELLS = 8
PADDING = 0.05    # 꽃과 셀 가장자리 여유 (셀 크기의 5%)

# 먼저 각 소스 셀에 flood fill 로 bg 투명화 (체크/회색 제거)
from collections import deque
SAT_THRESH = 25

def flood_transparent(a):
    H, W = a.shape[:2]
    rgb = a[:, :, :3].astype(np.int16)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    low_sat = sat < SAT_THRESH
    to_trans = np.zeros((H, W), dtype=bool)
    corners = [(0, 0), (W-1, 0), (0, H-1), (W-1, H-1)]
    for (cx, cy) in corners:
        if not low_sat[cy, cx] or to_trans[cy, cx]: continue
        q = deque([(cx, cy)])
        to_trans[cy, cx] = True
        while q:
            x, y = q.popleft()
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx, ny = x+dx, y+dy
                if 0 <= nx < W and 0 <= ny < H and low_sat[ny, nx] and not to_trans[ny, nx]:
                    to_trans[ny, nx] = True
                    q.append((nx, ny))
    a[to_trans, 3] = 0
    return a

files = sorted(glob.glob(os.path.join(CELLS_DIR, '*.png')))[:N_CELLS]
if len(files) < N_CELLS:
    print(f'ERROR: {CELLS_DIR} 에 {N_CELLS} 개 PNG 필요. 현재 {len(files)}개.')
    sys.exit(1)

canvas = Image.new('RGBA', (CELL_SIZE * N_CELLS, CELL_SIZE), (0, 0, 0, 0))

for i, path in enumerate(files):
    im = Image.open(path).convert('RGBA')
    a = np.array(im)
    # bg 투명화
    a = flood_transparent(a)
    alpha = a[:, :, 3]
    # flower tight bbox
    mask = alpha > 0
    if mask.sum() == 0:
        print(f'[{i+1}] empty')
        continue
    ys, xs = np.where(mask)
    bx, by = xs.min(), ys.min()
    bw = xs.max() - xs.min() + 1
    bh = ys.max() - ys.min() + 1
    # crop tight
    flower = Image.fromarray(a[by:by+bh, bx:bx+bw])
    # target 크기 (aspect 유지, 최대 변을 CELL_SIZE*(1-2*PADDING) 에 맞춤)
    max_dim = int(CELL_SIZE * (1 - 2 * PADDING))
    scale = min(max_dim / bw, max_dim / bh)
    tw = int(bw * scale); th = int(bh * scale)
    flower = flower.resize((tw, th), Image.LANCZOS)
    # 셀 중앙에 paste
    ox = i * CELL_SIZE + (CELL_SIZE - tw) // 2
    oy = (CELL_SIZE - th) // 2
    canvas.paste(flower, (ox, oy), flower)
    print(f'[{i+1}] bbox {bw}x{bh} → {tw}x{th} at cell center ({ox},{oy})')

canvas.save(OUT_NOTE)
canvas.save(OUT_HEAD)  # 같은 소스 사용 (홀드머리 전용 디자인 받으면 분리)
print(f'\n✓ 벚꽃_노트.png  {canvas.size}')
print(f'✓ 벚꽃_홀드머리.png  {canvas.size}')
