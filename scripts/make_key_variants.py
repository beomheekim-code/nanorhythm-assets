# -*- coding: utf-8 -*-
"""
key.png (딥 와인 베이스) → 8개 레인 색상 variant 생성.

베이스 key 의 "버튼 몸통 와인 그라데이션" 만 타겟 hue 로 변환.
벚꽃/LED/만다라 등 장식은 가급적 원본 유지 (과한 색변환 X).

전략: HSV 로 변환 후 sat 가 낮은 와인 톤만 타겟 hue 로 shift.
      꽃잎처럼 핑크/옐로우 강조 픽셀은 보존.
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image
import numpy as np
import colorsys

SRC = 'D:/nanorhythm-assets/nanorhythm-assets/skins/neon/key/key.png'
DST_DIR = 'D:/nanorhythm-assets/nanorhythm-assets/skins/neon/key'

# 레인별 타겟 hue (0~1) / sat 스케일 / val 스케일
# 벚꽃 UI 팩용 8색
LANE_TARGETS = [
    ('key_0', 0.927, 1.00, 1.00),  # 체리 핑크 #FF5A9E
    ('key_1', 0.870, 0.95, 0.95),  # 플럼 퍼플 #B04A9C
    ('key_2', 0.780, 0.85, 1.00),  # 라벤더 모브 #9B7AC4
    ('key_3', 0.840, 1.05, 1.05),  # 딥 마젠타 #D94BBE
    ('key_4', 0.945, 0.95, 1.10),  # 블러시 핑크 #FF85A8
    ('key_5', 0.030, 1.00, 1.10),  # 코랄 살몬 #FF8B6E
    ('key_6', 0.000, 0.80, 1.05),  # 로즈 골드 #E87A7A
    ('key_7', 0.050, 0.85, 1.15),  # 피치 #FFA87A
]


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
    return h, s, mx


def hsv_to_rgb_np(h, s, v):
    i = np.floor(h * 6).astype(np.int32)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    i = i % 6
    r = np.zeros_like(v); g = np.zeros_like(v); b = np.zeros_like(v)
    m0 = i == 0; r[m0]=v[m0]; g[m0]=t[m0]; b[m0]=p[m0]
    m1 = i == 1; r[m1]=q[m1]; g[m1]=v[m1]; b[m1]=p[m1]
    m2 = i == 2; r[m2]=p[m2]; g[m2]=v[m2]; b[m2]=t[m2]
    m3 = i == 3; r[m3]=p[m3]; g[m3]=q[m3]; b[m3]=v[m3]
    m4 = i == 4; r[m4]=t[m4]; g[m4]=p[m4]; b[m4]=v[m4]
    m5 = i == 5; r[m5]=v[m5]; g[m5]=p[m5]; b[m5]=q[m5]
    return r, g, b


def make_variant(base_rgba, target_hue, sat_mul, val_mul, out_path):
    a = base_rgba.copy()
    rgb = a[:, :, :3]
    h_orig, s_orig, v_orig = rgb_to_hsv_np(rgb)

    # 타겟 hue 로 완전 대체 (와인 본래 hue 무시)
    h_new = np.full_like(h_orig, target_hue)
    s_new = np.clip(s_orig * sat_mul, 0, 1)
    v_new = np.clip(v_orig * val_mul, 0, 1)

    r, g, b = hsv_to_rgb_np(h_new, s_new, v_new)
    rgb_new = np.stack([r, g, b], axis=-1) * 255.0
    rgb_new = np.clip(rgb_new, 0, 255).astype(np.uint8)

    out = np.dstack([rgb_new, a[:, :, 3]])
    Image.fromarray(out).save(out_path)


def main():
    base = np.array(Image.open(SRC).convert('RGBA'))
    print(f'베이스 key: {base.shape[1]}x{base.shape[0]}\n')

    for name, hue, sat_mul, val_mul in LANE_TARGETS:
        out_path = os.path.join(DST_DIR, f'{name}.png')
        make_variant(base, hue, sat_mul, val_mul, out_path)
        # 타겟 대표 색 RGB 출력
        tr, tg, tb = colorsys.hsv_to_rgb(hue, 0.7 * sat_mul, 0.9 * val_mul)
        hex_col = f'#{int(tr*255):02x}{int(tg*255):02x}{int(tb*255):02x}'
        print(f'  {name}.png  hue={hue:.3f}  sat×{sat_mul}  val×{val_mul}  → {hex_col}')
    print('\n완료.')


main()
