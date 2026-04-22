# -*- coding: utf-8 -*-
"""
key.png 녹색(#00FF00) 크로마키 제거 → 투명 배경 PNG.

HP 바와 동일 전략:
1. HSV 순녹색 kill
2. 연녹색 번짐 경계 감쇠 + RGB 보정
3. G > R, G > B 인 초록 halo 제거
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image
import numpy as np

SRC = 'D:/nanorhythm-assets/nanorhythm-assets/skins/neon/key/key.png'


def rgb_to_hsv_np(rgb):
    rgb = rgb.astype(np.float32) / 255.0
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx = np.max(rgb, axis=-1)
    mn = np.min(rgb, axis=-1)
    df = mx - mn
    h = np.zeros_like(mx)
    mask = df > 1e-6
    rmask = mask & (mx == r)
    gmask = mask & (mx == g) & ~rmask
    bmask = mask & (mx == b) & ~rmask & ~gmask
    h[rmask] = ((g[rmask] - b[rmask]) / df[rmask]) % 6
    h[gmask] = ((b[gmask] - r[gmask]) / df[gmask]) + 2
    h[bmask] = ((r[bmask] - g[bmask]) / df[bmask]) + 4
    h = h / 6.0
    s = np.where(mx > 1e-6, df / np.maximum(mx, 1e-6), 0)
    return np.stack([h, s, mx], axis=-1)


def process():
    im = Image.open(SRC).convert('RGBA')
    a = np.array(im)
    H, W = a.shape[:2]
    rgb = a[:, :, :3]
    alpha = np.full((H, W), 255, dtype=np.float32)

    hsv = rgb_to_hsv_np(rgb)
    hue, sat, val = hsv[..., 0], hsv[..., 1], hsv[..., 2]

    # Pass 1: 순녹색 kill (넓은 범위)
    pure_green = (hue >= 0.22) & (hue <= 0.48) & (sat > 0.25) & (val > 0.20)
    alpha[pure_green] = 0

    # Pass 1b: RGB 레벨 추가 kill (G dominant)
    r_pre = rgb[..., 0].astype(np.int32)
    g_pre = rgb[..., 1].astype(np.int32)
    b_pre = rgb[..., 2].astype(np.int32)
    g_dominant = (g_pre > r_pre + 25) & (g_pre > b_pre + 25) & (g_pre > 100)
    alpha[g_dominant] = 0

    # Pass 2: 연녹색 경계
    soft_green = (hue >= 0.18) & (hue <= 0.52) & (sat > 0.10) & (sat <= 0.25) & (val > 0.25)
    alpha[soft_green] *= 0.1
    rgb_f = rgb.astype(np.float32)
    rb_avg = (rgb_f[..., 0] + rgb_f[..., 2]) / 2
    rgb_f[..., 1] = np.where(soft_green, np.minimum(rgb_f[..., 1], rb_avg * 0.9), rgb_f[..., 1])
    rgb = np.clip(rgb_f, 0, 255).astype(np.uint8)

    # Pass 3: 초록 halo
    r_ch = rgb[..., 0].astype(np.int32)
    g_ch = rgb[..., 1].astype(np.int32)
    b_ch = rgb[..., 2].astype(np.int32)
    green_tint = (g_ch > r_ch) & (g_ch > b_ch) & (alpha > 10)
    if np.any(green_tint):
        new_g = np.minimum(r_ch, b_ch) * 0.8 + np.maximum(r_ch, b_ch) * 0.2
        rgb_f2 = rgb.astype(np.float32)
        rgb_f2[..., 1] = np.where(green_tint, new_g, rgb_f2[..., 1])
        rgb = np.clip(rgb_f2, 0, 255).astype(np.uint8)

    alpha_u8 = np.clip(alpha, 0, 255).astype(np.uint8)
    alpha_u8[alpha_u8 < 10] = 0

    out = np.dstack([rgb, alpha_u8])
    Image.fromarray(out).save(SRC)

    total = H * W
    opaque = int(np.sum(alpha_u8 > 240))
    killed = int(np.sum(alpha_u8 == 0))
    print(f'key  {W}x{H}  opaque={opaque}  killed={killed}  ({killed*100/total:.1f}% 투명)')


process()
print('완료.')
