# -*- coding: utf-8 -*-
"""
홀드몸통 — 32.png 레퍼런스: 네온관 유리 pill 느낌.

각 400×800 셀:
- 외곽 halo: pill 바깥 soft bloom (rim 색, quadratic fade)
- rim: 가장자리 ~3% 구간에 saturated+darkened 색 (네온관 유리 모서리)
- inner highlight: rim 바로 안쪽 ~7% 구간에 cream/white blend (유리 반사광)
- core: flower 색 살짝 채도 up, 세로 subtle gradient (중앙 살짝 어둡)
- top/bottom: flat — hold stretch 대응 (둥근 cap 은 head/tail 담당)

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

PILL_W_RATIO   = 0.72   # pill 폭 = 셀 폭의 72% (외곽 halo 여유 14%)
GLOW_OUT_PX    = 40     # pill 밖 halo 거리
RIM_W_RATIO    = 0.04   # rim 두께 (pill 폭 대비, 양쪽)
HL_W_RATIO     = 0.09   # 안쪽 흰 하이라이트 두께

def saturate(r, g, b, factor=1.0, scale=1.0):
    gray = (r + g + b) / 3.0
    r2 = int(np.clip((r - gray) * factor + gray, 0, 255) * scale)
    g2 = int(np.clip((g - gray) * factor + gray, 0, 255) * scale)
    b2 = int(np.clip((b - gray) * factor + gray, 0, 255) * scale)
    return (max(0,min(255,r2)), max(0,min(255,g2)), max(0,min(255,b2)))

src = Image.open(SRC_NOTE).convert('RGBA')
src_a = np.array(src)

canvas = np.zeros((BODY_CELL_H, BODY_CELL_W * N_CELLS, 4), dtype=np.uint8)

for i in range(N_CELLS):
    note_cell = src_a[:, i*NOTE_CELL_W:(i+1)*NOTE_CELL_W]
    alpha = note_cell[:, :, 3]
    rgb = note_cell[:, :, :3].astype(np.int16)
    sat = rgb.max(axis=2) - rgb.min(axis=2)
    mask = (sat >= 30) & (alpha >= 200)
    if mask.sum() < 100: mask = alpha >= 200
    fr = int(note_cell[:, :, 0][mask].mean())
    fg = int(note_cell[:, :, 1][mask].mean())
    fb = int(note_cell[:, :, 2][mask].mean())

    # 코어 — flower 색 살짝 채도 up (+ darken 소량)
    cr, cg, cb = saturate(fr, fg, fb, factor=1.20, scale=0.92)
    # rim — 네온관 유리 모서리: saturated + 살짝 darken (진한 색)
    rmr, rmg, rmb = saturate(fr, fg, fb, factor=1.5, scale=0.72)

    cell_x0 = i * BODY_CELL_W
    pill_w = int(BODY_CELL_W * PILL_W_RATIO)
    pill_x0 = cell_x0 + (BODY_CELL_W - pill_w) // 2
    pill_x1 = pill_x0 + pill_w

    rim_w = max(3, int(pill_w * RIM_W_RATIO))
    hl_w  = max(5, int(pill_w * HL_W_RATIO))

    # ★ 세로 그라데이션 + tail(위쪽) 투명도 페이드.
    #   py=0 (top, tail side) → darker + transparent
    #   py=H-1 (bottom, head side) → brighter + opaque
    for py in range(BODY_CELL_H):
        v = py / (BODY_CELL_H - 1)   # 0(top, tail) → 1(bottom, head)
        # 컬러 그라데이션: 밑(head)이 밝고 위(tail)로 갈수록 살짝 어둑 (smoke trail 느낌)
        vgrad = 0.78 + 0.22 * v      # 0.78 at top → 1.00 at bottom
        # 알파 페이드: 위쪽 40% 에서 부드럽게 사라짐 (꼬리 smoke 끝)
        #   t = 0 at top, 1 at 40% from top, 1 유지 below
        if v < 0.40:
            t = v / 0.40
            alpha_mul = t * t          # quadratic ease-in (매우 부드러운 페이드)
        else:
            alpha_mul = 1.0

        # pill 안쪽 영역
        for px in range(pill_x0, pill_x1):
            edge_dist = min(px - pill_x0, pill_x1 - 1 - px)
            if edge_dist < rim_w:
                # rim — saturated 진한 색
                t = edge_dist / rim_w  # 0(edge) → 1(rim inner)
                r = int(min(255, rmr * vgrad))
                g = int(min(255, rmg * vgrad))
                b = int(min(255, rmb * vgrad))
                # edge 바깥 쪽은 약간 soft 해서 anti-alias
                a = int(255 * (0.65 + 0.35 * t))
            elif edge_dist < rim_w + hl_w:
                # inner highlight — rim 직후 cream/white blend
                t = (edge_dist - rim_w) / hl_w  # 0(rim쪽) → 1(core쪽)
                hl = (1 - t)  # rim 쪽 강, core 쪽 약
                # 피크 90% white + 10% core
                peak_r = int(cr * 0.18 + 255 * 0.82)
                peak_g = int(cg * 0.18 + 255 * 0.82)
                peak_b = int(cb * 0.18 + 255 * 0.82)
                r = int(cr * (1-hl) + peak_r * hl)
                g = int(cg * (1-hl) + peak_g * hl)
                b = int(cb * (1-hl) + peak_b * hl)
                r = min(255, int(r * vgrad))
                g = min(255, int(g * vgrad))
                b = min(255, int(b * vgrad))
                a = 255
            else:
                # core — flower 색 saturated
                r = min(255, int(cr * vgrad))
                g = min(255, int(cg * vgrad))
                b = min(255, int(cb * vgrad))
                a = 255
            a = int(a * alpha_mul)
            canvas[py, px] = [r, g, b, a]

        # 외곽 halo — pill 양쪽 바깥
        for side in (-1, 1):
            for d in range(1, GLOW_OUT_PX + 1):
                px = (pill_x0 - d) if side < 0 else (pill_x1 - 1 + d)
                if px < 0 or px >= canvas.shape[1]: continue
                t = 1 - (d / GLOW_OUT_PX)  # 1(pill 인접) → 0(멀리)
                a = int(115 * t * t * alpha_mul)  # quadratic ease-out + tail fade
                if a <= 0: continue
                canvas[py, px] = [rmr, rmg, rmb, a]

    print(f'[{i+1}] flower=#{fr:02x}{fg:02x}{fb:02x} core=#{cr:02x}{cg:02x}{cb:02x} rim=#{rmr:02x}{rmg:02x}{rmb:02x}')

Image.fromarray(canvas).save(OUT_BODY)
print(f'\n✓ {OUT_BODY} ({canvas.shape[1]}x{canvas.shape[0]})')
