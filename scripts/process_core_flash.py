# -*- coding: utf-8 -*-
"""
core_flash 용 전용 처리 — Gemini 체커 halo 제거.

전략:
- 중심부 (d<400): 흰 코어 + 핑크 전이 보존
- 외곽 (d>400): R≈G≈B 중성 회색(체커) kill, 핑크만 유지
- 외곽끝 (d>950): 전부 kill
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image
import numpy as np
from scipy.ndimage import gaussian_filter

SRC = sys.argv[1] if len(sys.argv) > 1 else ''
DST = sys.argv[2] if len(sys.argv) > 2 else ''


def process():
    im = Image.open(SRC).convert('RGBA')
    a = np.array(im)
    H, W = a.shape[:2]
    r = a[:,:,0].astype(np.int32)
    g = a[:,:,1].astype(np.int32)
    b = a[:,:,2].astype(np.int32)
    alpha = a[:,:,3].astype(np.int32)

    cy, cx = H//2, W//2
    yy, xx = np.ogrid[:H, :W]
    dist2 = (yy-cy)**2 + (xx-cx)**2

    dist = np.sqrt(dist2).astype(np.int32)

    # Pass 1: RGB 강력 가우시안 블러 — 체커 패턴 완전 소거
    r = gaussian_filter(r.astype(np.float32), sigma=25).astype(np.int32)
    g = gaussian_filter(g.astype(np.float32), sigma=25).astype(np.int32)
    b = gaussian_filter(b.astype(np.float32), sigma=25).astype(np.int32)

    # Pass 2: 알파를 순수 radial 함수로 재구성 — 체커 dot 완전 제거
    # d=0~400: alpha=255 (불투명)
    # d=400~900: 255 → 0 smooth fade
    # d>900: 0
    alpha_radial = np.where(
        dist < 400,
        255,
        np.where(
            dist < 900,
            ((900 - dist) * 255 / 500).astype(np.int32),
            0
        )
    )
    alpha = alpha_radial.clip(0, 255)

    alpha_u8 = np.clip(alpha, 0, 255).astype(np.uint8)
    out = np.dstack([r, g, b, alpha_u8]).astype(np.uint8)
    Image.fromarray(out).save(DST)
    total = H * W
    killed = int(np.sum(alpha_u8 == 0))
    print(f'{W}x{H}  killed={killed} ({killed*100/total:.1f}%)')


process()
