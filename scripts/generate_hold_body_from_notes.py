# -*- coding: utf-8 -*-
"""
홀드몸통 심플 pill 생성 — 31.png 레퍼런스 기준.

각 레인 꽃 컬러 샘플링 → 세로 pill (rounded capsule):
- 양 옆 rounded edge
- 중앙 세로 하이라이트 줄 (white, 은은)
- 전체 세로 gradient (solid bright → subtle darker → bright)
- 상/하단 solid (head/tail 접합)

결과: 벚꽃_홀드몸통.png (3200×800), 8 레인 × 400×800.
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

# pill 설정
PILL_W_RATIO = 0.7       # pill 폭 = 셀 폭의 70%
EDGE_FADE_PX = 25        # 좌우 rounded edge fade 거리
HIGHLIGHT_W_RATIO = 0.12 # 중앙 하이라이트 줄 폭 (pill 폭 대비)
HIGHLIGHT_ALPHA = 100    # 하이라이트 투명도 (0-255)

src = Image.open(SRC_NOTE).convert('RGBA')
src_a = np.array(src)

canvas = np.zeros((BODY_CELL_H, BODY_CELL_W * N_CELLS, 4), dtype=np.uint8)

for i in range(N_CELLS):
    # 각 노트 셀 꽃 중심 컬러 샘플링 (opaque & saturated 픽셀 평균)
    note_cell = src_a[:, i*NOTE_CELL_W:(i+1)*NOTE_CELL_W]
    alpha = note_cell[:, :, 3]
    rgb = note_cell[:, :, :3].astype(np.int16)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    # 꽃잎 색 (sat >= 30 & alpha >= 200) 평균
    flower_mask = (sat >= 30) & (alpha >= 200)
    if flower_mask.sum() < 100:
        flower_mask = alpha >= 200
    fr = int(note_cell[:, :, 0][flower_mask].mean())
    fg = int(note_cell[:, :, 1][flower_mask].mean())
    fb = int(note_cell[:, :, 2][flower_mask].mean())

    # 밝은 버전 (pill 기본색) + 진한 버전 (edge shadow)
    bright = (min(255, fr+20), min(255, fg+20), min(255, fb+20))
    deep   = (max(0, fr-30), max(0, fg-30), max(0, fb-30))

    cell_x0 = i * BODY_CELL_W
    pill_w = int(BODY_CELL_W * PILL_W_RATIO)
    pill_x0 = cell_x0 + (BODY_CELL_W - pill_w) // 2

    for py in range(BODY_CELL_H):
        # 세로 gradient (solid 전구간, 상/하 완전 solid)
        # 중간 살짝 brighter (pill 입체감)
        v = abs(py - BODY_CELL_H / 2) / (BODY_CELL_H / 2)  # 0(중앙) ~ 1(끝)
        r = int(bright[0] * (1 - v * 0.15) + deep[0] * v * 0.15)
        g = int(bright[1] * (1 - v * 0.15) + deep[1] * v * 0.15)
        b = int(bright[2] * (1 - v * 0.15) + deep[2] * v * 0.15)

        for px_local in range(pill_w):
            px = pill_x0 + px_local
            # 좌우 rounded edge fade (alpha)
            edge_dist = min(px_local, pill_w - 1 - px_local)
            if edge_dist < EDGE_FADE_PX:
                edge_alpha = int(255 * edge_dist / EDGE_FADE_PX)
            else:
                edge_alpha = 255
            # edge 에 가까울수록 약간 더 진한 색 (입체감)
            edge_v = 1.0 - min(1.0, edge_dist / (pill_w / 2))  # 1(edge) ~ 0(center)
            r_p = int(r * (1 - edge_v * 0.15) + deep[0] * edge_v * 0.15)
            g_p = int(g * (1 - edge_v * 0.15) + deep[1] * edge_v * 0.15)
            b_p = int(b * (1 - edge_v * 0.15) + deep[2] * edge_v * 0.15)
            canvas[py, px] = [r_p, g_p, b_p, edge_alpha]

        # 중앙 하이라이트 줄 (white, 은은)
        hl_w = int(pill_w * HIGHLIGHT_W_RATIO)
        hl_x0 = pill_x0 + (pill_w - hl_w) // 2
        for px_local in range(hl_w):
            px = hl_x0 + px_local
            # soft 중앙 fade
            hl_v = 1.0 - abs(px_local - hl_w / 2) / (hl_w / 2)
            hl_a = int(HIGHLIGHT_ALPHA * hl_v)
            # 현재 pill 색 위에 white 반투명 블렌드
            cr, cg, cb, ca = canvas[py, px]
            if ca > 0:
                blend_a = hl_a / 255.0
                canvas[py, px, 0] = int(cr * (1 - blend_a) + 255 * blend_a)
                canvas[py, px, 1] = int(cg * (1 - blend_a) + 255 * blend_a)
                canvas[py, px, 2] = int(cb * (1 - blend_a) + 255 * blend_a)

    print(f'[{i+1}] flower color = #{fr:02x}{fg:02x}{fb:02x}, pill {pill_w}×{BODY_CELL_H}')

Image.fromarray(canvas).save(OUT_BODY)
print(f'\n✓ {OUT_BODY} (3200×800)')
