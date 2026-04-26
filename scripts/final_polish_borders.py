"""
final polish — halo + 코어 밖 fuzz 제거.

이전 단계 (Edge Extension + zero-tolerance spill) 후 진단:
- halo: alpha 1-29 (faint 외곽) → 시각적 haze 원인
- 코어 (alpha > 200) 에서 멀리 떨어진 mid-alpha (alpha 30-180) → 떠다니는 fuzz

처리:
1. 강한 코어만 추출 (alpha > 200)
2. 코어를 4px 확장 → soft zone (anti-alias edge 보존 영역)
3. soft zone 밖의 모든 alpha 값 0 (떠다니는 fuzz 완전 제거)
4. soft zone 안에서도 halo (alpha < 30) 는 0 (faint haze 차단)
5. 코어 alpha gamma 보정 → 살짝 더 sharp (선택적)
"""
import os
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, distance_transform_edt

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

DILATE_PX = 4  # core 확장 px (anti-alias edge 보존 영역)
HALO_KILL = 30  # alpha < 30 → 0

for rel in SPRITES:
    p = os.path.join(DIR, rel)
    if not os.path.exists(p):
        print(f'SKIP: {rel}'); continue
    img = Image.open(p).convert('RGBA')
    arr = np.array(img).astype(np.uint8)
    a = arr[:,:,3]
    h, w = arr.shape[:2]

    # 1. 코어 마스크
    core = a > 200

    # 2. 코어 확장 (anti-alias 영역)
    soft_zone = binary_dilation(core, iterations=DILATE_PX)

    # 3. soft zone 밖 → alpha 0
    out_zone = ~soft_zone & (a > 0)
    arr[out_zone, 3] = 0
    killed_outside = int(out_zone.sum())

    # 4. soft zone 안 halo → 0
    in_halo = soft_zone & (a > 0) & (a < HALO_KILL)
    arr[in_halo, 3] = 0
    killed_halo = int(in_halo.sum())

    # 5. Edge Extension 재실행 (out_zone alpha=0 으로 바뀐 픽셀 RGB 도 letter 색으로)
    a2 = arr[:,:,3]
    opaque = a2 > 0
    if opaque.any():
        _, indices = distance_transform_edt(~opaque, return_distances=True, return_indices=True)
        ny, nx = indices[0], indices[1]
        transparent = ~opaque
        arr[transparent, 0] = arr[ny[transparent], nx[transparent], 0]
        arr[transparent, 1] = arr[ny[transparent], nx[transparent], 1]
        arr[transparent, 2] = arr[ny[transparent], nx[transparent], 2]

    Image.fromarray(arr, 'RGBA').save(p, optimize=True, compress_level=9)
    sz = os.path.getsize(p)/1024
    print(f'{rel}: out_zone_killed={killed_outside}, halo_killed={killed_halo}, {sz:.0f} KB')

print('\nDone.')
