# -*- coding: utf-8 -*-
"""
Gemini_Generated_Image_2vjdn02vjdn02vjd.png (네온 핑크 링) 마커/체커 제거.

전략:
1. 체커 배경(어두운 와인 R<80, G<40, B<50) → 알파 0
2. 우하단 스파클 워터마크 영역 마스크 (150px 이내 코너) → 알파 0
3. 핑크 링 본체 (R>120 OR sat 높은 핑크) 보존
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image
import numpy as np

import sys as _sys
SRC = _sys.argv[1] if len(_sys.argv) > 1 else 'D:/nanorhythm-assets/nanorhythm-assets/skins/neon/hit_effect/Gemini_Generated_Image_2vjdn02vjdn02vjd.png'
DST = _sys.argv[2] if len(_sys.argv) > 2 else 'D:/nanorhythm-assets/nanorhythm-assets/skins/neon/hit_effect/_neon_ring_clean.png'


def process():
    im = Image.open(SRC).convert('RGBA')
    a = np.array(im)
    H, W = a.shape[:2]
    r, g, b = a[:,:,0].astype(np.int32), a[:,:,1].astype(np.int32), a[:,:,2].astype(np.int32)
    alpha = np.full((H, W), 255, dtype=np.int32)

    brightness = r + g + b
    chroma = r - g

    # Pass 1: 어두운 중성 체커만 kill (R ≈ G ≈ B 근처 회색 + 어두움)
    # 골드 링 내부 디테일 보존 위해 R<170 일괄 kill 은 제거
    neutral_ch = np.abs(r - g) + np.abs(r - b) + np.abs(g - b)
    alpha[(brightness < 150) & (neutral_ch < 30)] = 0

    # Pass 2: 중간 밝기 + 저채도 (그라데이션 배경)
    mid_low_chroma = (brightness >= 150) & (brightness < 250) & (neutral_ch < 30)
    alpha[mid_low_chroma] = 0

    # Pass 3: 파란 톤(checker) 킬 — 블루 도미넌트 제거
    #   핑크(R>G) 와 골드(R>=G, G>>B) 모두 유지되는 조건: B < R AND B < G + 20
    cold = (b > r) | (b > g + 20)
    alpha[cold] = 0

    # Pass 4: 우하단 워터마크 마스크 (250x250)
    wm_size = 250
    alpha[H-wm_size:, W-wm_size:] = 0

    # Pass 5: 원형 도넛 마스크 — 링 영역(외곽 820px ~ 내부 520px) 밖 싹 제거
    cy, cx = H // 2, W // 2
    yy, xx = np.ogrid[:H, :W]
    dist2 = (yy - cy)**2 + (xx - cx)**2
    outside_ring = dist2 > 820**2   # 외곽 밖
    inside_hole = dist2 < 520**2    # 중앙 구멍 안
    alpha[outside_ring] = 0
    alpha[inside_hole] = 0

    # Pass 6: 남은 halo dot-pattern 가우시안 smoothing
    from scipy.ndimage import gaussian_filter
    alpha_f = alpha.astype(np.float32)
    alpha_blurred = gaussian_filter(alpha_f, sigma=6)
    alpha = np.maximum(alpha_f, alpha_blurred).clip(0, 255).astype(np.int32)
    alpha[alpha < 20] = 0

    alpha_u8 = np.clip(alpha, 0, 255).astype(np.uint8)
    out = np.dstack([r, g, b, alpha_u8]).astype(np.uint8)
    Image.fromarray(out).save(DST)

    total = H * W
    killed = int(np.sum(alpha_u8 == 0))
    print(f'{W}x{H}  killed={killed} ({killed*100/total:.1f}%)')


process()
print(f'saved: {DST}')
