# -*- coding: utf-8 -*-
"""
일반 체커 제거 스크립트.
RGB 가우시안 블러 (sigma=15) + 알파 블러 (sigma=8) 로 체커 패턴 뭉개기.
원본 형태/실루엣은 유지, 내부 dot-pattern 만 smooth out.

사용: python smooth_checker.py <in.png> <out.png> [rgb_sigma] [alpha_sigma]
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image
import numpy as np
from scipy.ndimage import gaussian_filter

SRC = sys.argv[1]
DST = sys.argv[2]
RGB_SIGMA = float(sys.argv[3]) if len(sys.argv) > 3 else 15
ALPHA_SIGMA = float(sys.argv[4]) if len(sys.argv) > 4 else 8


def process():
    im = Image.open(SRC).convert('RGBA')
    a = np.array(im)
    H, W = a.shape[:2]
    r = a[:,:,0].astype(np.float32)
    g = a[:,:,1].astype(np.float32)
    b = a[:,:,2].astype(np.float32)
    alpha = a[:,:,3].astype(np.float32)

    # RGB 블러 — 체커 패턴 뭉개기
    r = gaussian_filter(r, sigma=RGB_SIGMA)
    g = gaussian_filter(g, sigma=RGB_SIGMA)
    b = gaussian_filter(b, sigma=RGB_SIGMA)

    # 알파 블러 — dot pattern 알파 smoothing
    alpha = gaussian_filter(alpha, sigma=ALPHA_SIGMA)

    # 너무 작은 잔티 제거
    alpha[alpha < 10] = 0

    out = np.dstack([
        np.clip(r, 0, 255).astype(np.uint8),
        np.clip(g, 0, 255).astype(np.uint8),
        np.clip(b, 0, 255).astype(np.uint8),
        np.clip(alpha, 0, 255).astype(np.uint8),
    ])
    Image.fromarray(out).save(DST)
    print(f'{W}x{H}  rgb_sigma={RGB_SIGMA}  alpha_sigma={ALPHA_SIGMA}')


process()
