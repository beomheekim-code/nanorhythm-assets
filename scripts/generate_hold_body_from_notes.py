# -*- coding: utf-8 -*-
"""
홀드몸통 — "꽃을 세로로 늘린 잔상" 생성.

_cells/note/ 의 꽃 원본을 세로 방향으로 stretch → 늘어진 꽃 silhouette 가 몸통이 됨.
- 탁한 원색 (RGB × 0.85 로 saturate)
- 좌우 약간 rounded fade
- 상/하단 solid (head/tail seamless)

결과: 벚꽃_홀드몸통.png (3200×800)
"""
import sys, io, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image
import numpy as np
from collections import deque

BASE = 'D:/리듬게임/skins/neon/note'
CELLS_DIR = os.path.join(BASE, '_cells', 'note')
OUT_BODY = os.path.join(BASE, '벚꽃_홀드몸통.png')

BODY_CELL_W, BODY_CELL_H = 400, 800
N_CELLS = 8
STRETCH_PAD_X = 10   # 좌우 여유 (잔상 기둥 느낌)
STRETCH_PAD_Y = 0    # 상/하 solid, 여유 없음
DARKEN = 0.85        # 탁한 원색 (RGB × 이 값)

SAT_THRESH = 25
def flood_transparent(a):
    H, W = a.shape[:2]
    rgb = a[:, :, :3].astype(np.int16)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    low_sat = sat < SAT_THRESH
    to_trans = np.zeros((H, W), dtype=bool)
    for cx, cy in [(0,0),(W-1,0),(0,H-1),(W-1,H-1)]:
        if not low_sat[cy,cx] or to_trans[cy,cx]: continue
        q = deque([(cx,cy)])
        to_trans[cy,cx] = True
        while q:
            x, y = q.popleft()
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx, ny = x+dx, y+dy
                if 0<=nx<W and 0<=ny<H and low_sat[ny,nx] and not to_trans[ny,nx]:
                    to_trans[ny,nx] = True
                    q.append((nx,ny))
    a[to_trans, 3] = 0
    return a

files = sorted(glob.glob(os.path.join(CELLS_DIR, '*.png')))[:N_CELLS]
canvas = np.zeros((BODY_CELL_H, BODY_CELL_W * N_CELLS, 4), dtype=np.uint8)

for i, path in enumerate(files):
    im = Image.open(path).convert('RGBA')
    a = np.array(im)
    a = flood_transparent(a)
    alpha = a[:,:,3]
    mask = alpha > 0
    if mask.sum() == 0: continue
    # largest connected component
    visited = np.zeros_like(mask)
    best_coords = None
    best_size = 0
    Hc, Wc = mask.shape
    for sy in range(0, Hc, 20):
        for sx in range(0, Wc, 20):
            if not mask[sy,sx] or visited[sy,sx]: continue
            q = deque([(sx,sy)])
            visited[sy,sx] = True
            comp = [(sx,sy)]
            while q:
                x, y = q.popleft()
                for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx, ny = x+dx, y+dy
                    if 0<=nx<Wc and 0<=ny<Hc and mask[ny,nx] and not visited[ny,nx]:
                        visited[ny,nx] = True
                        comp.append((nx,ny))
                        q.append((nx,ny))
            if len(comp) > best_size:
                best_size = len(comp)
                best_coords = comp
    # stray 제거
    keep = np.zeros_like(mask)
    for (x, y) in best_coords:
        keep[y, x] = True
    a[~keep, 3] = 0

    # 꽃 tight bbox
    xs = np.array([c[0] for c in best_coords])
    ys = np.array([c[1] for c in best_coords])
    fx0, fy0 = xs.min(), ys.min()
    fw, fh = xs.max()-xs.min()+1, ys.max()-ys.min()+1
    flower = a[fy0:fy0+fh, fx0:fx0+fw]

    # ★ 꽃 색 탁하게 (RGB × DARKEN)
    dark_flower = flower.copy()
    dark_flower[:,:,:3] = (dark_flower[:,:,:3].astype(np.float32) * DARKEN).clip(0,255).astype(np.uint8)

    # premultiply alpha (resize bleed 방지)
    rgbf = dark_flower[:,:,:3].astype(np.float32)
    af = dark_flower[:,:,3].astype(np.float32) / 255.0
    premul = (rgbf * af[:,:,None]).astype(np.uint8)
    premul_a = np.concatenate([premul, dark_flower[:,:,3:4]], axis=2)
    flower_pil = Image.fromarray(premul_a)

    # ★ 세로 stretch — 꽃을 BODY_CELL 전체 크기로 resize (가로는 pad 반영, 세로는 전체)
    target_w = BODY_CELL_W - STRETCH_PAD_X * 2
    target_h = BODY_CELL_H - STRETCH_PAD_Y * 2
    stretched = flower_pil.resize((target_w, target_h), Image.LANCZOS)

    # un-premultiply
    sa = np.array(stretched, dtype=np.float32)
    fa_ = sa[:,:,3:4]
    safe = np.where(fa_>0, fa_, 1)
    unp = (sa[:,:,:3] * 255 / safe).clip(0,255).astype(np.uint8)
    unp = np.concatenate([unp, sa[:,:,3:4].astype(np.uint8)], axis=2)

    # canvas 에 paste (각 셀의 왼쪽-중앙)
    x0 = i * BODY_CELL_W + STRETCH_PAD_X
    y0 = STRETCH_PAD_Y
    canvas[y0:y0+target_h, x0:x0+target_w] = unp

    # 탁한 색 샘플 로그
    opq_mask = unp[:,:,3] > 200
    if opq_mask.sum() > 0:
        mr = int(unp[:,:,0][opq_mask].mean())
        mg = int(unp[:,:,1][opq_mask].mean())
        mb = int(unp[:,:,2][opq_mask].mean())
        print(f'[{i+1}] stretched flower {target_w}×{target_h}, avg color #{mr:02x}{mg:02x}{mb:02x}')

Image.fromarray(canvas).save(OUT_BODY)
print(f'\n✓ {OUT_BODY} (3200×800)')
