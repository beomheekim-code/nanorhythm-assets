# -*- coding: utf-8 -*-
"""
_cells/key_overlay/ 의 8 개별 셀을 사용해 벚꽃_노트.png 재생성.
기존 _cells/key_overlay/01~08.png 는 꽃이 셀 상단에 있지만 노트용으론 중앙 필요.
→ 각 셀에서 꽃 tight bbox 찾아서 400×400 square 캔버스 중앙에 재배치.
결과: 3200×400 RGBA (8셀 × 400×400 각각).

홀드머리용도 동일 소스라 복사 → 벚꽃_홀드머리.png.
"""
import sys, io, os, glob, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image
import numpy as np

# ── Skin 파라미터 ────────────────────────────────────────────────────────
# 사용법: python rebuild_note_from_cells.py [skin_id]
#   skin_id 생략 시 'neon' 기본. skins/{id}/manifest.json 에서 경로 읽음.
SKIN_ID = sys.argv[1] if len(sys.argv) > 1 else 'neon'
SKINS_ROOT = 'D:/리듬게임/skins'
MANIFEST_PATH = os.path.join(SKINS_ROOT, SKIN_ID, 'manifest.json')
with open(MANIFEST_PATH, encoding='utf-8') as f:
    manifest = json.load(f)

BASE      = os.path.join(SKINS_ROOT, SKIN_ID)
CELLS_DIR = os.path.join(BASE, manifest['cellsDir'])
OUT_NOTE  = os.path.join(BASE, manifest['files']['note'])
# silhouette 출력은 holdHead 와 별개 — manifest 에 holdHeadSilhouette 있으면 사용, 없으면 생략
_silh_rel = manifest.get('files', {}).get('holdHeadSilhouette')
OUT_HEAD  = os.path.join(BASE, _silh_rel) if _silh_rel else None

CELL_SIZE = manifest.get('cellSize', 400)
N_CELLS   = manifest.get('nCells', 8)
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
    # flower tight bbox — 단, 가장 큰 connected component 만 사용 (stray 조각 제거)
    mask = alpha > 0
    if mask.sum() == 0:
        print(f'[{i+1}] empty')
        continue
    # connected components (BFS)
    visited = np.zeros_like(mask, dtype=bool)
    best_size = 0
    best_coords = None
    H_c, W_c = mask.shape
    for sy in range(0, H_c, 20):
        for sx in range(0, W_c, 20):
            if not mask[sy, sx] or visited[sy, sx]: continue
            # BFS
            q = deque([(sx, sy)])
            visited[sy, sx] = True
            comp_coords = [(sx, sy)]
            while q:
                x, y = q.popleft()
                for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx, ny = x+dx, y+dy
                    if 0<=nx<W_c and 0<=ny<H_c and mask[ny,nx] and not visited[ny,nx]:
                        visited[ny,nx] = True
                        comp_coords.append((nx, ny))
                        q.append((nx, ny))
            if len(comp_coords) > best_size:
                best_size = len(comp_coords)
                best_coords = comp_coords
    # stray components → 투명화
    keep_mask = np.zeros_like(mask)
    for (x, y) in best_coords:
        keep_mask[y, x] = True
    a[~keep_mask, 3] = 0
    # 가장 큰 component 기준 bbox
    xs_c = np.array([c[0] for c in best_coords])
    ys_c = np.array([c[1] for c in best_coords])
    bx, by = xs_c.min(), ys_c.min()
    bw = xs_c.max() - xs_c.min() + 1
    bh = ys_c.max() - ys_c.min() + 1
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
print(f'\n✓ {OUT_NOTE}  {canvas.size}')

# ★ silhouette 출력 — manifest 에 holdHeadSilhouette 정의된 경우만 생성.
#   현 시스템에선 holdHead = note sprite 공유 (body 앞뒤 동일 꽃), silhouette 사용 안 함.
#   향후 단색 스킨용 옵션으로 유지.
if OUT_HEAD is None:
    print('(silhouette skip — manifest.files.holdHeadSilhouette 미정의)')
    sys.exit(0)

head_arr = np.array(canvas)

def _saturate(r, g, b, factor=1.3, darken=0.9):
    gray = (r + g + b) / 3
    r2 = int(np.clip((r - gray) * factor + gray, 0, 255) * darken)
    g2 = int(np.clip((g - gray) * factor + gray, 0, 255) * darken)
    b2 = int(np.clip((b - gray) * factor + gray, 0, 255) * darken)
    return (r2, g2, b2)

for i in range(N_CELLS):
    x0, x1 = i * CELL_SIZE, (i + 1) * CELL_SIZE
    cell = head_arr[:, x0:x1]
    alpha = cell[:, :, 3]
    mask = alpha > 0
    if mask.sum() == 0: continue
    # saturated & opaque 픽셀 중심으로 꽃 주요 색 측정
    rgb = cell[:, :, :3].astype(np.int16)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    core = mask & (sat >= 30) & (alpha >= 200)
    if core.sum() < 50: core = mask
    mr = int(cell[:, :, 0][core].mean())
    mg = int(cell[:, :, 1][core].mean())
    mb = int(cell[:, :, 2][core].mean())
    # saturated 변환
    sr, sg, sb = _saturate(mr, mg, mb, 1.3, 0.9)
    # flower 영역 전체 해당 단색으로 채움 (alpha 는 기존 유지 → 안티앨리어스 보존)
    cell[mask, 0] = sr
    cell[mask, 1] = sg
    cell[mask, 2] = sb
    print(f'  [{i+1}] solid silhouette color #{sr:02x}{sg:02x}{sb:02x}')

Image.fromarray(head_arr).save(OUT_HEAD)
print(f'✓ {OUT_HEAD}  {canvas.size} (silhouette)')
