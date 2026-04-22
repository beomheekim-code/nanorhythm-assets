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

    # Pass 0: 완전 까만 픽셀 (R<30) kill — 체커 잔재, metallic shading 은 R>=50 이라 영향 없음
    alpha[r < 30] = 0

    # Pass 1: 원형 도넛 마스크 (hole + outside 싹 제거)
    cy, cx = H // 2, W // 2
    yy, xx = np.ogrid[:H, :W]
    dist2 = (yy - cy)**2 + (xx - cx)**2
    outside_ring = dist2 > 820**2
    inside_hole = dist2 < 650**2
    alpha[outside_ring] = 0
    alpha[inside_hole] = 0

    # Pass 2: 우하단 워터마크 (link 밖이라 이미 kill 됐지만 안전)
    wm_size = 250
    alpha[H-wm_size:, W-wm_size:] = 0

    alpha_u8 = np.clip(alpha, 0, 255).astype(np.uint8)
    out = np.dstack([r, g, b, alpha_u8]).astype(np.uint8)
    Image.fromarray(out).save(DST)

    total = H * W
    killed = int(np.sum(alpha_u8 == 0))
    print(f'{W}x{H}  killed={killed} ({killed*100/total:.1f}%)')


process()
print(f'saved: {DST}')
