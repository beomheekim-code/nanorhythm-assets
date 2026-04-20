# -*- coding: utf-8 -*-
"""
홀드몸통 — 31.png 레퍼런스: saturated 색 pill + 내부 세로 하이라이트 줄 (캡슐 glass).

각 셀:
- 세로 rounded pill (캡슐 모양, 상/하 solid)
- 꽃 색을 saturated 버전으로 변환 (채도 boost, 명도 다운)
- 내부에 희미한 세로 하이라이트 줄 2개 (좌우 25/75% 위치, pill 의 유리 반사 느낌)
- 좌우 fade (rounded edge)

결과: 3200×800 RGBA.
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image
import numpy as np

BASE = 'D:/리듬게임/skins/neon/note'
SRC_NOTE = os.path.join(BASE, '벚꽃_노트.png')
OUT_BODY = os.path.join(BASE, '벚꽃_홀드몸통.png')

NOTE_CELL_W = 400
BODY_CELL_W, BODY_CELL_H = 400, 800
N_CELLS = 8

PILL_W_RATIO = 0.72   # pill 폭 = 셀 폭의 72%
EDGE_FADE_PX = 22     # 좌우 rounded fade 거리

# 내부 하이라이트 줄 (31.png 처럼 2개)
STRIPE_POSITIONS = [0.25, 0.75]  # pill 폭 대비 위치 (좌 25%, 우 75%)
STRIPE_W_RATIO = 0.06            # 각 줄 폭 (pill 폭 대비)
STRIPE_ALPHA = 90                # 하이라이트 alpha

def saturate(r, g, b, factor=1.3, darken=0.9):
    """RGB 채도 증가 + 살짝 darken → 탁한 원색 느낌"""
    # HSV 변환 없이 간단 saturation: (c - gray) * factor + gray
    gray = (r + g + b) / 3
    r2 = int(np.clip((r - gray) * factor + gray, 0, 255) * darken)
    g2 = int(np.clip((g - gray) * factor + gray, 0, 255) * darken)
    b2 = int(np.clip((b - gray) * factor + gray, 0, 255) * darken)
    return (r2, g2, b2)

src = Image.open(SRC_NOTE).convert('RGBA')
src_a = np.array(src)

canvas = np.zeros((BODY_CELL_H, BODY_CELL_W * N_CELLS, 4), dtype=np.uint8)

for i in range(N_CELLS):
    # 각 노트 셀에서 꽃 중심 컬러
    note_cell = src_a[:, i*NOTE_CELL_W:(i+1)*NOTE_CELL_W]
    alpha = note_cell[:, :, 3]
    rgb = note_cell[:, :, :3].astype(np.int16)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    mask = (sat >= 30) & (alpha >= 200)
    if mask.sum() < 100: mask = alpha >= 200
    fr = int(note_cell[:, :, 0][mask].mean())
    fg = int(note_cell[:, :, 1][mask].mean())
    fb = int(note_cell[:, :, 2][mask].mean())
    # saturated 버전
    pr, pg, pb = saturate(fr, fg, fb, factor=1.3, darken=0.9)

    cell_x0 = i * BODY_CELL_W
    pill_w = int(BODY_CELL_W * PILL_W_RATIO)
    pill_x0 = cell_x0 + (BODY_CELL_W - pill_w) // 2

    for py in range(BODY_CELL_H):
        for px_local in range(pill_w):
            px = pill_x0 + px_local
            # 좌우 fade
            edge_dist = min(px_local, pill_w - 1 - px_local)
            if edge_dist < EDGE_FADE_PX:
                edge_alpha = int(255 * edge_dist / EDGE_FADE_PX)
            else:
                edge_alpha = 255
            # 기본 fill
            canvas[py, px] = [pr, pg, pb, edge_alpha]

        # 내부 세로 하이라이트 줄 2개 (좌 25%, 우 75%)
        for stripe_pos in STRIPE_POSITIONS:
            sx_center = pill_x0 + int(pill_w * stripe_pos)
            stripe_w = max(2, int(pill_w * STRIPE_W_RATIO))
            for dx in range(-stripe_w//2, stripe_w//2 + 1):
                px = sx_center + dx
                if pill_x0 <= px < pill_x0 + pill_w:
                    # 줄 중앙에서 멀수록 흐릿
                    dist = abs(dx) / (stripe_w / 2 if stripe_w > 1 else 1)
                    hl_a = int(STRIPE_ALPHA * (1 - dist))
                    cr, cg, cb, ca = canvas[py, px]
                    if ca > 0 and hl_a > 0:
                        blend = hl_a / 255.0
                        # white 반투명 블렌드
                        canvas[py, px, 0] = int(cr * (1 - blend) + 255 * blend)
                        canvas[py, px, 1] = int(cg * (1 - blend) + 255 * blend)
                        canvas[py, px, 2] = int(cb * (1 - blend) + 255 * blend)

    print(f'[{i+1}] flower=#{fr:02x}{fg:02x}{fb:02x} → pill=#{pr:02x}{pg:02x}{pb:02x}, {pill_w}×{BODY_CELL_H}')

Image.fromarray(canvas).save(OUT_BODY)
print(f'\n✓ {OUT_BODY} (3200×800)')
