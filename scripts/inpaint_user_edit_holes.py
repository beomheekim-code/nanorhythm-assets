"""
유저가 직접 지운 나뭇가지 영역 (중간 크기 hole) + 우하단 Gemini 워터마크 자리 빵꾸
를 주변 나무색으로 inpaint.

처리 영역:
1. 내부 hole (binary_fill_holes) — 크기 <=1500 px 만 inpaint (user-edit 메움).
   나뭇가지 사이 큰 sky patch (수만 px) 는 유지.
2. 이미지 하단 30% 영역의 투명 픽셀 중 주변 opaque (거리 <= 150 px) 있는 곳 inpaint.
   = Gemini 워터마크 제거된 자리.
"""
import os
import numpy as np
from PIL import Image
from scipy.ndimage import binary_fill_holes, distance_transform_edt, label

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
CONTAINER = os.path.join(ROOT, 'skins', 'neon', 'container')

HOLE_MAX = 1500
WM_REGION_Y_RATIO = 0.7       # 하단 30%
WM_INPAINT_MAX_DIST = 150     # nearest opaque 이 이만큼 이내에 있어야 inpaint

for name in ['left', 'right']:
    src = os.path.join(CONTAINER, f'sakura_tree_{name}.png')
    img = Image.open(src).convert('RGBA')
    arr = np.array(img)
    h, w = arr.shape[:2]
    print(f'{name}: {w}x{h}, {os.path.getsize(src)/1024:.0f} KB')

    a = arr[:, :, 3]
    mask = a > 50

    # === 1) 내부 hole inpaint (<=1500px) ===
    filled = binary_fill_holes(mask)
    holes = filled & ~mask
    lbl, n_labels = label(holes)
    sizes = np.bincount(lbl.ravel())
    internal_target = np.zeros_like(holes, dtype=bool)
    fill_count = 0
    fill_px = 0
    sky_count = 0
    sky_px = 0
    for li in range(1, n_labels + 1):
        if sizes[li] <= HOLE_MAX:
            internal_target |= (lbl == li)
            fill_count += 1
            fill_px += int(sizes[li])
        else:
            sky_count += 1
            sky_px += int(sizes[li])
    print(f'  내부 hole: inpaint {fill_count} ({fill_px} px), sky 유지 {sky_count} ({sky_px} px)')

    # === 2) 하단 워터마크 영역 inpaint (거리 <= 150px 제한) ===
    dist, (iy, ix) = distance_transform_edt(~mask, return_distances=True, return_indices=True)
    y_start = int(h * WM_REGION_Y_RATIO)
    wm_region = np.zeros_like(mask, dtype=bool)
    wm_region[y_start:, :] = True
    wm_target = wm_region & ~mask & (dist <= WM_INPAINT_MAX_DIST)
    wm_px = int(wm_target.sum())
    print(f'  워터마크 영역 inpaint: {wm_px} px (거리 <= {WM_INPAINT_MAX_DIST})')

    # 합쳐서 inpaint
    total_target = internal_target | wm_target
    if total_target.sum() > 0:
        hy, hx = np.where(total_target)
        sy, sx = iy[hy, hx], ix[hy, hx]
        arr[hy, hx, 0] = arr[sy, sx, 0]
        arr[hy, hx, 1] = arr[sy, sx, 1]
        arr[hy, hx, 2] = arr[sy, sx, 2]
        arr[hy, hx, 3] = arr[sy, sx, 3]

    # 알파 threshold
    a_new = arr[:, :, 3].astype(np.int32)
    a_new = np.where(a_new < 40, 0, a_new)
    arr[:, :, 3] = a_new.astype(np.uint8)

    final = Image.fromarray(arr, 'RGBA')
    final.save(src, optimize=True, compress_level=9)
    print(f'  saved: {os.path.getsize(src)/1024:.0f} KB')
