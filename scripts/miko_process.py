"""
miko_taiko 캐릭터 PNG 풀 처리:
1. chroma green (#00ff00) 제거 → alpha 0
2. zero-tolerance spill suppression
3. core-dilation 으로 떠다니는 fuzz 제거
4. halo (alpha < 80) kill
5. 우하단 watermark zone (200x200) clear
6. Edge Extension
7. opaque bbox crop (캐릭터 둘러싼 minimum bounding box)
8. 다운스케일 1024 → 320 (인게임 사이즈, 4x compression)
"""
import os
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, distance_transform_edt, label

DIR = r'D:\nanorhythm-assets\nanorhythm-assets\skins\miko_taiko'
FILES = ['standby_near_normal.png', 'strike_near_normal.png',
         'standby_far_normal.png', 'strike_far_normal.png',
         'standby_near_fever.png', 'strike_near_fever.png',
         'standby_far_fever.png', 'strike_far_fever.png',
         'miss.png',
         'idle.png']
TARGET_H = 320  # 인게임 사이즈 (좌측 하단 캐릭터)
WM_W, WM_H = 200, 200  # 우하단 watermark zone

def process(arr):
    arr = arr.copy().astype(np.int16)
    h, w = arr.shape[:2]

    # 0. 우하단 watermark zone 강제 #00ff00 (chroma 단계서 자동 제거)
    arr[h-WM_H:h, w-WM_W:w, 0] = 0
    arr[h-WM_H:h, w-WM_W:w, 1] = 255
    arr[h-WM_H:h, w-WM_W:w, 2] = 0

    r, g, b, a = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]

    # 1. chroma alpha kill (원본 green 기준)
    g_excess = np.maximum(0, g - np.maximum(r, b))
    alpha_mul = np.clip(1 - g_excess / 60.0, 0, 1) ** 1.2
    new_a = (a * alpha_mul).astype(np.int16)
    new_a = np.where(new_a < 25, 0, new_a)
    arr[:,:,3] = new_a
    a = arr[:,:,3]

    # 2. spill suppression (남은 opaque 의 green tint 제거)
    spill = (g > np.maximum(r, b)) & (a > 0)
    arr[:,:,1] = np.where(spill, np.maximum(r, b), g)

    # 3. dust + core 외 fuzz
    mask = a > 50
    lab, n = label(mask)
    if n > 0:
        sizes = np.bincount(lab.ravel()); sizes[0] = 0
        keep = sizes > 200
        keep_mask = keep[lab]
        arr[mask & ~keep_mask, 3] = 0
        a = arr[:,:,3]

    core = a > 200
    soft = binary_dilation(core, iterations=4)
    arr[~soft & (a > 0), 3] = 0
    a = arr[:,:,3]

    # 4. halo (alpha 1-79) kill
    halo = (a > 0) & (a < 80)
    arr[halo, 3] = 0

    # 5. mid-alpha < 130 도 kill (sharp outline)
    weak = (arr[:,:,3] > 0) & (arr[:,:,3] < 130)
    arr[weak, 3] = 0

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

# 1단계: 모든 파일 chroma cleanup → 메모리에 보관
cleaned_all = {}
for f in FILES:
    p = os.path.join(DIR, f)
    if not os.path.exists(p):
        print(f'SKIP {f}: not found'); continue
    arr = np.array(Image.open(p).convert('RGBA'))
    cleaned_all[f] = process(arr)

# 2단계: union bbox 계산 (모든 프레임 캐릭터 둘러싸는 최대 영역)
union = None
for arr in cleaned_all.values():
    img = Image.fromarray(arr, 'RGBA')
    bb = img.getbbox()
    if not bb: continue
    if union is None:
        union = list(bb)
    else:
        union[0] = min(union[0], bb[0])
        union[1] = min(union[1], bb[1])
        union[2] = max(union[2], bb[2])
        union[3] = max(union[3], bb[3])
print(f'union bbox: {union}')

# 3단계: union bbox 로 모든 프레임 crop + 같은 크기로 다운스케일
ux1, uy1, ux2, uy2 = union
uw, uh = ux2 - ux1, uy2 - uy1
scale = TARGET_H / uh
target_w = max(1, int(uw * scale))
print(f'union {uw}x{uh} → resized {target_w}x{TARGET_H}')

for f, arr in cleaned_all.items():
    img = Image.fromarray(arr, 'RGBA').crop((ux1, uy1, ux2, uy2))
    img = img.resize((target_w, TARGET_H), Image.LANCZOS)
    p = os.path.join(DIR, f)
    img.save(p, optimize=True, compress_level=9)
    sz = os.path.getsize(p) / 1024
    print(f'{f}: {img.size}, {sz:.0f} KB')
print('Done.')
