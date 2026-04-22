# -*- coding: utf-8 -*-
"""
ring_pink, ring_gold, core_flash — 체커 패턴 제거 2차 시도.

전략 (알파 보존, RGB 만 infill):
1. 솔리드 영역 (alpha > 200) 의 RGB 만 소스로 사용
2. 해당 RGB 를 큰 반경으로 가우시안 블러 (확산)
3. 소스 영역의 기여도 weight 도 동일 블러 → 정규화
4. 대상 픽셀 (alpha ≤ 200) 의 RGB 를 블러 결과로 교체
5. 알파는 그대로 유지 → 모양/페더 보존, RGB 체커만 제거
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image
import numpy as np
from scipy.ndimage import gaussian_filter

BASE = 'D:/nanorhythm-assets/nanorhythm-assets/skins/neon/hit_effect'
FILES = ['ring_pink.png', 'ring_gold.png', 'core_flash.png']
SIGMA = 25  # 반경 (px) — 크면 더 매끄러움


def process(fn):
    path = os.path.join(BASE, fn)
    im = Image.open(path).convert('RGBA')
    a = np.array(im).astype(np.float32)
    H, W = a.shape[:2]
    rgb = a[:, :, :3]
    alpha = a[:, :, 3]

    # 솔리드 영역만 소스
    src_mask = (alpha > 200).astype(np.float32)  # 0/1
    # RGB × 마스크 (소스 영역만)
    rgb_masked = rgb * src_mask[..., None]

    # 각 채널별 확산 + weight 확산 → 정규화
    blurred = np.zeros_like(rgb)
    weight = gaussian_filter(src_mask, sigma=SIGMA)
    weight_safe = np.maximum(weight, 1e-4)
    for ch in range(3):
        bl = gaussian_filter(rgb_masked[..., ch], sigma=SIGMA)
        blurred[..., ch] = bl / weight_safe

    # weight 가 너무 작은 지역 (소스 픽셀 근처 전혀 없음) → 전역 평균 RGB fallback
    if np.any(src_mask > 0):
        global_mean = rgb[src_mask > 0].mean(axis=0)
    else:
        global_mean = np.array([128, 128, 128])
    fallback_mask = weight < 0.01
    for ch in range(3):
        blurred[..., ch] = np.where(fallback_mask, global_mean[ch], blurred[..., ch])

    # 대상 픽셀 (alpha ≤ 200 이지만 > 0) 만 blurred 로 교체
    target_mask = (alpha > 0) & (alpha <= 200)
    out_rgb = rgb.copy()
    for ch in range(3):
        out_rgb[..., ch] = np.where(target_mask, blurred[..., ch], rgb[..., ch])

    out_rgb = np.clip(out_rgb, 0, 255).astype(np.uint8)
    alpha_u8 = np.clip(alpha, 0, 255).astype(np.uint8)
    out = np.dstack([out_rgb, alpha_u8])
    Image.fromarray(out).save(path)

    total = H * W
    src_px = int(src_mask.sum())
    tgt_px = int(target_mask.sum())
    print(f'{fn}  {W}x{H}  source={src_px}  target(infill)={tgt_px}  kept_alpha')


for fn in FILES:
    process(fn)
print('완료.')
