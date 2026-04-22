# -*- coding: utf-8 -*-
"""
hp_bar.png 녹색(#00FF00) 크로마키 제거 → 투명 배경 PNG.

전략:
1. HSV 변환
2. 녹색 hue 범위(H≈100~140°, S>0.4, V>0.3) → alpha=0
3. 경계 부드러운 잎/가지 가장자리 녹색 번짐 제거
   - 초록빛이 섞인 부분은 saturation 기반 ramp
4. RGB 저채도 잎색도 녹색 제거 후 탈색 보정
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image
import numpy as np

SRC = 'D:/nanorhythm-assets/nanorhythm-assets/skins/neon/hp_bar/hp_bar.png'


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

    # ─── Pass 1: 순녹색 kill ───
    # 녹색 hue 0.27~0.42 (≈96°~150°)
    # 단, 와인/딥브라운 가지/꽃 제외
    pure_green = (hue >= 0.25) & (hue <= 0.45) & (sat > 0.35) & (val > 0.25)
    alpha[pure_green] = 0

    # ─── Pass 2: 연녹색/초록 번짐 경계 ───
    # (Gemini 가장자리 antialias 에서 옅은 초록 섞임)
    soft_green = (hue >= 0.22) & (hue <= 0.48) & (sat > 0.15) & (sat <= 0.35) & (val > 0.3)
    # 이 영역은 alpha 를 감쇠 + RGB 를 R/B 쪽으로 보정 (초록 제거)
    alpha[soft_green] *= 0.2  # 거의 투명
    # RGB 초록 성분 감쇠
    rgb_f = rgb.astype(np.float32)
    g_ch = rgb_f[..., 1]
    # 초록 빼고 R,B 평균으로 대체
    rb_avg = (rgb_f[..., 0] + rgb_f[..., 2]) / 2
    rgb_f[..., 1] = np.where(soft_green, np.minimum(g_ch, rb_avg * 0.9), g_ch)
    rgb = np.clip(rgb_f, 0, 255).astype(np.uint8)

    # ─── Pass 3: 가지/꽃 경계 초록 halo 제거 ───
    # 꽃잎/가지의 외곽선에 살짝 초록 번진 경우: G > R 이고 G > B 이면서 alpha 살아있는 픽셀
    r_ch = rgb[..., 0].astype(np.int32)
    g_ch = rgb[..., 1].astype(np.int32)
    b_ch = rgb[..., 2].astype(np.int32)
    green_tint = (g_ch > r_ch) & (g_ch > b_ch) & (alpha > 10)
    if np.any(green_tint):
        # G 를 R,B 평균으로 낮춤
        new_g = np.minimum(r_ch, b_ch) * 0.8 + np.maximum(r_ch, b_ch) * 0.2
        rgb_f2 = rgb.astype(np.float32)
        rgb_f2[..., 1] = np.where(green_tint, new_g, rgb_f2[..., 1])
        rgb = np.clip(rgb_f2, 0, 255).astype(np.uint8)

    # ─── Pass 4: 낮은 alpha 정리 ───
    alpha_u8 = np.clip(alpha, 0, 255).astype(np.uint8)
    alpha_u8[alpha_u8 < 10] = 0

    out = np.dstack([rgb, alpha_u8])
    Image.fromarray(out).save(SRC)

    total = H * W
    opaque = int(np.sum(alpha_u8 > 240))
    killed = int(np.sum(alpha_u8 == 0))
    print(f'hp_bar  {W}x{H}  opaque={opaque}  killed={killed}  ({killed*100/total:.1f}% 투명)')


process()
print('완료.')
