# -*- coding: utf-8 -*-
"""
노트 sprite 기반 홀드몸통 생성 — "잔상(afterimage)" 느낌.

각 노트 꽃(벚꽃_노트.png cell) 에서:
1. 꽃 중심 컬러 샘플링 → 그라데이션 base color
2. 꽃 silhouette 를 알파 낮춰서 세로로 3개 반복 (잔상 echo)
3. 좌우는 은은한 graident pill (기둥 느낌)
4. 상/하단 solid (head/tail 과 접합)

결과: 벚꽃_홀드몸통.png (3200×800, 8 셀 × 400×800).
런타임 부하 0 — 그냥 static PNG.
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image, ImageFilter
import numpy as np

BASE = 'D:/리듬게임/skins/neon/note'
SRC_NOTE = os.path.join(BASE, '벚꽃_노트.png')    # 3200×400
OUT_BODY = os.path.join(BASE, '벚꽃_홀드몸통.png') # 3200×800

NOTE_CELL_W = 400
BODY_CELL_W, BODY_CELL_H = 400, 800
N_CELLS = 8

# 각 셀 내 기둥(pill) 설정
PILL_W_RATIO = 0.65   # 셀 폭의 65% (270px)
PILL_TOP_PAD = 0       # 상/하 패딩 — 0 (solid top/bottom for seamless connect)

# 잔상 echo flower 설정
ECHO_COUNT = 3        # 세로로 반복할 잔상 수
ECHO_ALPHA = 120      # 잔상 불투명도 (0-255)
ECHO_SCALE = 0.5      # 원본 꽃 대비 축소 비율

src = Image.open(SRC_NOTE).convert('RGBA')
src_a = np.array(src)

canvas = Image.new('RGBA', (BODY_CELL_W * N_CELLS, BODY_CELL_H), (0, 0, 0, 0))
cvs_a = np.array(canvas)

for i in range(N_CELLS):
    # 원본 note 셀 추출
    note_cell = src_a[:, i*NOTE_CELL_W:(i+1)*NOTE_CELL_W]
    alpha = note_cell[:, :, 3]
    if alpha.sum() == 0:
        print(f'[{i+1}] empty note cell')
        continue
    # 꽃 중심 컬러 (alpha>200 인 픽셀들의 평균)
    opq = alpha > 200
    if opq.sum() == 0:
        opq = alpha > 100
    base_r = int(note_cell[:, :, 0][opq].mean())
    base_g = int(note_cell[:, :, 1][opq].mean())
    base_b = int(note_cell[:, :, 2][opq].mean())
    # 약간 밝게 (기둥 색상 — 꽃보다 부드러운 톤)
    pill_r = min(255, int(base_r * 0.7 + 255 * 0.3))
    pill_g = min(255, int(base_g * 0.7 + 255 * 0.3))
    pill_b = min(255, int(base_b * 0.7 + 255 * 0.3))

    cell_x0 = i * BODY_CELL_W
    pill_w = int(BODY_CELL_W * PILL_W_RATIO)
    pill_x = cell_x0 + (BODY_CELL_W - pill_w) // 2

    # 1. 세로 기둥 — rounded pill (세로 그라데이션)
    pill = np.zeros((BODY_CELL_H, pill_w, 4), dtype=np.uint8)
    # 좌우로 alpha gradient (pill 곡선 느낌) + 중앙 살짝 더 진함
    for px in range(pill_w):
        # 좌우 edge 페이드 (rounded)
        edge_dist = min(px, pill_w - 1 - px)
        edge_fade = min(1.0, edge_dist / 30.0)
        for py in range(BODY_CELL_H):
            pill[py, px, 0] = pill_r
            pill[py, px, 1] = pill_g
            pill[py, px, 2] = pill_b
            # 상/하 solid (head/tail 접합), 중간 살짝 밝게
            center_dist = abs(py - BODY_CELL_H / 2) / (BODY_CELL_H / 2)
            base_alpha = 200 + int(center_dist * 30)  # 200~230
            pill[py, px, 3] = int(min(255, base_alpha * edge_fade))
    # pill 을 canvas 에 paste
    cvs_a[:, pill_x:pill_x + pill_w] = pill

    # 2. 잔상 echo flower — 꽃 silhouette 을 낮은 alpha 로 세로 반복
    note_pil = Image.fromarray(note_cell)
    # crop tight
    alpha_2d = note_cell[:, :, 3]
    ys, xs = np.where(alpha_2d > 0)
    if len(xs) == 0: continue
    fbx, fby = xs.min(), ys.min()
    fbw = xs.max() - xs.min() + 1
    fbh = ys.max() - ys.min() + 1
    flower_crop = note_pil.crop((fbx, fby, fbx + fbw, fby + fbh))
    # 축소
    echo_w = int(pill_w * ECHO_SCALE)
    echo_h = int(echo_w * fbh / fbw)
    flower_small = flower_crop.resize((echo_w, echo_h), Image.LANCZOS)
    # alpha 낮추기
    fs_a = np.array(flower_small)
    fs_a[:, :, 3] = (fs_a[:, :, 3].astype(np.int32) * ECHO_ALPHA // 255).astype(np.uint8)
    flower_faded = Image.fromarray(fs_a)
    # 세로로 ECHO_COUNT 개 배치 (균등 간격)
    cvs_pil = Image.fromarray(cvs_a)
    for k in range(ECHO_COUNT):
        # 상/하단 피하고 중앙 영역에 배치
        ey = int((k + 1) * BODY_CELL_H / (ECHO_COUNT + 1)) - echo_h // 2
        ex = cell_x0 + (BODY_CELL_W - echo_w) // 2
        cvs_pil.alpha_composite(flower_faded, (ex, ey))
    cvs_a = np.array(cvs_pil)

    print(f'[{i+1}] base=({base_r},{base_g},{base_b}), pill={pill_w}x{BODY_CELL_H}, echoes={ECHO_COUNT}')

Image.fromarray(cvs_a).save(OUT_BODY)
print(f'\n✓ {OUT_BODY} (3200×800)')
