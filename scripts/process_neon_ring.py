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

    # Pass 1: R < 170 전부 kill (ring_pink 와 동일 — 어두운 영역 확실히 제거)
    alpha[r < 170] = 0

    # Pass 2: 중간 밝기 + 저채도 (그라데이션 배경)
    mid_low_chroma = (brightness >= 150) & (brightness < 250) & (chroma < 50)
    alpha[mid_low_chroma] = 0

    # Pass 3: 파란 톤(checker) 킬 — 블루 도미넌트 제거
    #   핑크(R>G) 와 골드(R>=G, G>>B) 모두 유지되는 조건: B < R AND B < G + 20
    cold = (b > r) | (b > g + 20)
    alpha[cold] = 0

    # Pass 4: 우하단 워터마크 마스크 (250x250)
    wm_size = 250
    alpha[H-wm_size:, W-wm_size:] = 0

    # Pass 5-pre: 가우시안 smoothing 먼저 — halo dot-pattern 뭉개기
    from scipy.ndimage import gaussian_filter
    alpha_f = alpha.astype(np.float32)
    alpha_blurred = gaussian_filter(alpha_f, sigma=6)
    alpha = np.maximum(alpha_f, alpha_blurred).clip(0, 255).astype(np.int32)
    alpha[alpha < 20] = 0

    # Pass 5: 원형 도넛 마스크 — 링 영역 밖 싹 제거 (hard cut, blur 이후 적용)
    cy, cx = H // 2, W // 2
    yy, xx = np.ogrid[:H, :W]
    dist2 = (yy - cy)**2 + (xx - cx)**2
    outside_ring = dist2 > 820**2   # 외곽 밖
    inside_hole = dist2 < 520**2    # 중앙 구멍 안 (ring_pink 와 동일)
    alpha[outside_ring] = 0
    alpha[inside_hole] = 0

    # Pass 7: RGB 가우시안 블러 — 솔리드 링 body 안의 체커 패턴 뭉개기
    r_s = gaussian_filter(r.astype(np.float32), sigma=8)
    g_s = gaussian_filter(g.astype(np.float32), sigma=8)
    b_s = gaussian_filter(b.astype(np.float32), sigma=8)
    # alpha 있는 영역만 스무딩 적용
    mask = (alpha > 200)
    r = np.where(mask, r_s, r).astype(np.int32)
    g = np.where(mask, g_s, g).astype(np.int32)
    b = np.where(mask, b_s, b).astype(np.int32)

    alpha_u8 = np.clip(alpha, 0, 255).astype(np.uint8)
    out = np.dstack([np.clip(r,0,255), np.clip(g,0,255), np.clip(b,0,255), alpha_u8]).astype(np.uint8)
    Image.fromarray(out).save(DST)

    total = H * W
    killed = int(np.sum(alpha_u8 == 0))
    print(f'{W}x{H}  killed={killed} ({killed*100/total:.1f}%)')


process()
print(f'saved: {DST}')
