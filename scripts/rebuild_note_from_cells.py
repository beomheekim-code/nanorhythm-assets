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
CELLS_DIR = os.path.join(BASE, '_cells', 'note')
OUT_NOTE = os.path.join(BASE, '벚꽃_노트.png')
OUT_HEAD = os.path.join(BASE, '벚꽃_홀드머리.png')

CELL_SIZE = 400   # 최종 셀당 크기 (정사각)
N_CELLS = 8
PADDING = 0.05    # 꽃과 셀 가장자리 여유 (셀 크기의 5%)

# 단일 flood fill — corners 에서 저채도 연결 영역 제거.
# SAT_THRESH 25: bg 만 제거, 꽃 body 는 전부 보존.
# 45 로 올리면 lilac/pale-pink 처럼 sat < 60 인 pastel 꽃이 eaten 됨.
# halo 가 일부 남지만 flower 훼손보다 나음. 완벽한 제거는 유저가 각 셀 수작업 필요.
from collections import deque
SAT_THRESH = 25

def flood_transparent(a):
    H, W = a.shape[:2]
    rgb = a[:, :, :3].astype(np.int16)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    low_sat = sat < SAT_THRESH
    to_trans = np.zeros((H, W), dtype=bool)
    for (cx, cy) in [(0, 0), (W-1, 0), (0, H-1), (W-1, H-1)]:
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
    cropped = a[by:by+bh, bx:bx+bw].copy()
    # ★ premultiplied alpha resize — 투명 영역 RGB(gray) 가 opaque 가장자리로 bleed 하는 것 방지.
    #   PIL 의 RGBA resize 는 pre-multiply 안 해서 halo 생성. 수동 처리.
    rgb_f = cropped[:, :, :3].astype(np.float32)
    alpha_f = cropped[:, :, 3].astype(np.float32) / 255.0
    premul_rgb = (rgb_f * alpha_f[:, :, np.newaxis]).astype(np.uint8)
    premul_arr = np.concatenate([premul_rgb, cropped[:, :, 3:4]], axis=2)
    flower = Image.fromarray(premul_arr)
    # target 크기 (aspect 유지)
    max_dim = int(CELL_SIZE * (1 - 2 * PADDING))
    scale = min(max_dim / bw, max_dim / bh)
    tw = int(bw * scale); th = int(bh * scale)
    flower = flower.resize((tw, th), Image.LANCZOS)
    # un-premultiply: RGB = premul_RGB / alpha
    f_arr = np.array(flower, dtype=np.float32)
    fa = f_arr[:, :, 3:4]
    safe_a = np.where(fa > 0, fa, 1)
    unpremul = (f_arr[:, :, :3] * 255 / safe_a).clip(0, 255).astype(np.uint8)
    unpremul = np.concatenate([unpremul, f_arr[:, :, 3:4].astype(np.uint8)], axis=2)
    flower = Image.fromarray(unpremul)
    # 셀 중앙에 paste
    ox = i * CELL_SIZE + (CELL_SIZE - tw) // 2
    oy = (CELL_SIZE - th) // 2
    canvas.paste(flower, (ox, oy), flower)
    print(f'[{i+1}] bbox {bw}x{bh} → {tw}x{th} at cell center ({ox},{oy})')

canvas.save(OUT_NOTE)
canvas.save(OUT_HEAD)  # 같은 소스 사용 (홀드머리 전용 디자인 받으면 분리)
print(f'\n✓ 벚꽃_노트.png  {canvas.size}')
print(f'✓ 벚꽃_홀드머리.png  {canvas.size}')
