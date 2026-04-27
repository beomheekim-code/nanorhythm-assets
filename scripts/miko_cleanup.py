"""
miko_taiko 캐릭터 PNG 풀 클린업.
1. left 파일들에서 좌상단 라벨 zone (1-1, 2-2 등) 클리어
2. chroma green (#00ff00) 제거 → alpha 0
3. Edge Extension (알파=0 RGB → 가장 가까운 letter 픽셀)
4. halo (alpha < 30) 제거
5. flip → right 버전 자동 생성
"""
import os
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, distance_transform_edt, label

DIR = r'D:\nanorhythm-assets\nanorhythm-assets\skins\miko_taiko'
PAIRS = ['idle', 'hit', 'idle_fever', 'hit_fever', 'miss']

# 라벨 zone — 좌상단 코너 ~70x40 정도 (1-1, 2-2 같은 텍스트)
LABEL_W, LABEL_H = 70, 40

def cleanup(arr):
    arr = arr.copy().astype(np.int16)
    h, w = arr.shape[:2]

    # 좌상단 라벨 zone → 강제 #00ff00 (chroma 단계에서 자동 제거됨)
    arr[0:LABEL_H, 0:LABEL_W, 0] = 0
    arr[0:LABEL_H, 0:LABEL_W, 1] = 255
    arr[0:LABEL_H, 0:LABEL_W, 2] = 0
    arr[0:LABEL_H, 0:LABEL_W, 3] = 255

    r, g, b, a = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]

    # 1. zero-tolerance spill suppression
    spill = (g > np.maximum(r, b)) & (a > 0)
    arr[:,:,1] = np.where(spill, np.maximum(r, b), g)
    g = arr[:,:,1]

    # 2. chroma alpha kill
    g_orig = np.array(arr[:,:,1])  # spill 후 g
    g_excess = np.maximum(0, g_orig - np.maximum(r, b))
    alpha_mul = np.clip(1 - g_excess / 60.0, 0, 1) ** 1.2
    new_a = (a * alpha_mul).astype(np.int16)
    new_a = np.where(new_a < 25, 0, new_a)
    arr[:,:,3] = new_a
    a = arr[:,:,3]

    # 3. dust removal
    mask = a > 50
    lab, n = label(mask)
    if n > 0:
        sizes = np.bincount(lab.ravel()); sizes[0] = 0
        keep = sizes > 80
        keep_mask = keep[lab]
        arr[mask & ~keep_mask, 3] = 0
        a = arr[:,:,3]

    # 4. core dilation 으로 떠다니는 fuzz 제거
    core = a > 200
    soft = binary_dilation(core, iterations=4)
    out_zone = ~soft & (a > 0)
    arr[out_zone, 3] = 0
    a = arr[:,:,3]

    # 5. halo (alpha 1-29) kill
    halo = (a > 0) & (a < 30)
    arr[halo, 3] = 0

    # 6. Edge Extension
    a2 = arr[:,:,3]
    opaque = a2 > 0
    if opaque.any():
        _, idx = distance_transform_edt(~opaque, return_distances=True, return_indices=True)
        ny, nx = idx[0], idx[1]
        transparent = ~opaque
        arr[transparent, 0] = arr[ny[transparent], nx[transparent], 0]
        arr[transparent, 1] = arr[ny[transparent], nx[transparent], 1]
        arr[transparent, 2] = arr[ny[transparent], nx[transparent], 2]

    return np.clip(arr, 0, 255).astype(np.uint8)

for pair in PAIRS:
    L = os.path.join(DIR, f'{pair}_left.png')
    R = os.path.join(DIR, f'{pair}_right.png')
    if not os.path.exists(L):
        print(f'SKIP {pair}: left missing'); continue

    # left 클린업
    im = Image.open(L).convert('RGBA')
    arr = np.array(im)
    cleaned = cleanup(arr)
    Image.fromarray(cleaned, 'RGBA').save(L, optimize=True, compress_level=9)
    sz_l = os.path.getsize(L) / 1024

    # right = flip(cleaned left)
    flipped = np.fliplr(cleaned)
    Image.fromarray(flipped, 'RGBA').save(R, optimize=True, compress_level=9)
    sz_r = os.path.getsize(R) / 1024

    a_count = int((cleaned[:,:,3] > 50).sum())
    print(f'{pair}: opaque={a_count}px, left={sz_l:.0f}KB, right={sz_r:.0f}KB')

print('\nDone.')
