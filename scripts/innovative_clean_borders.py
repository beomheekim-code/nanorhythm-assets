"""
혁신적 테두리 클린업 — 알파=0 픽셀 RGB bleeding 해결.

원인 진단:
- score_label.png 알파=0 픽셀 RGB = (11, 243, 2) (순수 chroma green)
- canvas drawImage 가 bilinear 필터링 시 알파=0 픽셀 RGB 가 letter edge 로 번짐
- 결과: 글자 테두리에 초록 fringe → "지저분"하게 보임

해결책: Edge Extension (premultiply 친화)
- 알파=0 픽셀의 RGB를 가장 가까운 letter 픽셀 RGB 로 채움
- 알파는 그대로 0 (투명 유지)
- 스케일링 시 RGB 가 letter 색과 일관 → fringe 사라짐

추가 stage:
- spill suppression: g > max(r,b) → g = max(r,b) (zero tolerance)
- chroma alpha kill: g_excess 강한 픽셀 alpha 추가 감쇠
- dust removal: 작은 connected component 제거
"""
import os
import numpy as np
from PIL import Image
from scipy.ndimage import label, distance_transform_edt, binary_dilation

DIR = r'D:\nanorhythm-assets\nanorhythm-assets\skins\neon'
SPRITES = [
    'combo_text/combo_label.png',
    'judgment_text/judge_perfect.png',
    'judgment_text/judge_great.png',
    'judgment_text/judge_good.png',
    'judgment_text/judge_miss.png',
    'score_text/score_label.png',
    'score_text/max_combo_label.png',
    'fever/fever_burst.png',
    'numbers/numbers_atlas.png',
]

for rel in SPRITES:
    p = os.path.join(DIR, rel)
    if not os.path.exists(p):
        print(f'SKIP: {rel}'); continue
    img = Image.open(p).convert('RGBA')
    arr = np.array(img).astype(np.int16)
    r, g, b, a = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]
    h, w = arr.shape[:2]

    # === 1. zero-tolerance spill suppression ===
    spill = (g > np.maximum(r, b)) & (a > 0)
    arr[:,:,1] = np.where(spill, np.maximum(r, b), g)
    g = arr[:,:,1]
    spill_count = int(spill.sum())

    # === 2. chroma alpha kill (g_excess 강한 곳 alpha 추가 감쇠) ===
    g_excess_orig = np.maximum(0, np.array(Image.open(p).convert('RGBA'))[:,:,1].astype(int) - np.maximum(r, b))
    alpha_mul = np.clip(1 - g_excess_orig / 60.0, 0, 1) ** 1.2
    new_a = (a * alpha_mul).astype(np.int16)
    new_a = np.where(new_a < 25, 0, new_a)  # 작은 잔존 알파 제거
    arr[:,:,3] = new_a
    a = arr[:,:,3]
    killed_alpha = int((a == 0).sum() - (np.array(Image.open(p).convert('RGBA'))[:,:,3] == 0).sum())

    # === 3. connected component dust removal ===
    mask = a > 50
    lab, n = label(mask)
    if n > 0:
        sizes = np.bincount(lab.ravel()); sizes[0] = 0
        keep = sizes > 80
        keep_mask = keep[lab]
        dust = mask & ~keep_mask
        arr[dust, 3] = 0
        a = arr[:,:,3]
        dust_count = int(dust.sum())
    else:
        dust_count = 0

    # === 4. Edge Extension ★ (RGB bleed 차단의 핵심) ===
    opaque = a > 0
    if opaque.any():
        # 각 transparent 픽셀에 대해 가장 가까운 opaque 픽셀 좌표 찾기
        _, indices = distance_transform_edt(~opaque, return_distances=True, return_indices=True)
        ny, nx = indices[0], indices[1]
        # transparent 픽셀의 RGB 를 가장 가까운 opaque 픽셀의 RGB 로 교체
        transparent = ~opaque
        arr[transparent, 0] = arr[ny[transparent], nx[transparent], 0]
        arr[transparent, 1] = arr[ny[transparent], nx[transparent], 1]
        arr[transparent, 2] = arr[ny[transparent], nx[transparent], 2]

    # === 5. final spill check on extended RGB (transparent 영역도 클린) ===
    r2, g2, b2 = arr[:,:,0], arr[:,:,1], arr[:,:,2]
    spill2 = g2 > np.maximum(r2, b2)
    arr[:,:,1] = np.where(spill2, np.maximum(r2, b2), g2)

    # 저장
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGBA').save(p, optimize=True, compress_level=9)
    sz = os.path.getsize(p)/1024
    print(f'{rel}: spill={spill_count}, dust={dust_count}, edge-ext={int((~opaque).sum())}, {sz:.0f} KB')

print('\nDone.')
