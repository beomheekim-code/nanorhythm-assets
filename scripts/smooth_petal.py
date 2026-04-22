# -*- coding: utf-8 -*-
"""
petal 전용 — 외곽선 유지 + 내부 hollow fill + halo 체커 블러.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image
import numpy as np
from scipy.ndimage import gaussian_filter, binary_fill_holes, binary_dilation

SRC = sys.argv[1]
DST = sys.argv[2]


def process():
    im = Image.open(SRC).convert('RGBA')
    a = np.array(im)
    H, W = a.shape[:2]
    r = a[:,:,0].astype(np.float32)
    g = a[:,:,1].astype(np.float32)
    b = a[:,:,2].astype(np.float32)
    alpha = a[:,:,3].astype(np.float32)

    # Pass 1: 솔리드 외곽선 mask
    solid_mask = (alpha > 220) & (r > g + 30)

    # Pass 2: 외곽선 채워 내부 메꿈
    dilated = binary_dilation(solid_mask, iterations=5)
    filled = binary_fill_holes(dilated)
    inside = filled & ~solid_mask
    if solid_mask.sum() > 0:
        mean_r = float(r[solid_mask].mean())
        mean_g = float(g[solid_mask].mean())
        mean_b = float(b[solid_mask].mean())
        # 내부 파스텔 핑크
        fill_r = min(255, mean_r * 1.25)
        fill_g = min(255, mean_g * 1.45)
        fill_b = min(255, mean_b * 1.30)
        r[inside] = fill_r
        g[inside] = fill_g
        b[inside] = fill_b

    # Pass 3: 마스크 가우시안으로 경계 부드럽게 + threshold 로 깔끔한 outline
    mask_f = filled.astype(np.float32) * 255
    mask_smooth = gaussian_filter(mask_f, sigma=12)
    # threshold 100 이상 → 불투명 core, 30~100 → fade, <30 → 투명
    alpha = np.where(
        mask_smooth > 140,
        255,
        np.where(mask_smooth > 60, (mask_smooth - 60) * 255 / 80, 0)
    ).astype(np.float32)
    # RGB 도 솔리드 근처만 smooth
    rgb_full = np.stack([r, g, b], axis=-1)
    rgb_smooth = np.stack([
        gaussian_filter(r, sigma=2),
        gaussian_filter(g, sigma=2),
        gaussian_filter(b, sigma=2),
    ], axis=-1)
    r, g, b = rgb_smooth[:,:,0], rgb_smooth[:,:,1], rgb_smooth[:,:,2]
    alpha[alpha < 15] = 0

    out = np.dstack([
        np.clip(r, 0, 255).astype(np.uint8),
        np.clip(g, 0, 255).astype(np.uint8),
        np.clip(b, 0, 255).astype(np.uint8),
        np.clip(alpha, 0, 255).astype(np.uint8),
    ])
    Image.fromarray(out).save(DST)
    print(f'{W}x{H}  solid_outline={solid_mask.sum()}  filled_interior={inside.sum()}')


process()
