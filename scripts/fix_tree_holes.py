"""
sakura_tree_left/right 홀 fill — 크기 기준으로 구분.
- <= 300 px: trunk 핀홀 → 주변 opaque 색 inpaint
- > 300 px: 나뭇가지 사이 sky patch → 투명 유지

백업: versions/sakura_tree_pre_holefill_v2/ (원본 raw) 에서 항상 새로 시작.
"""
import os
import shutil
import numpy as np
from PIL import Image
from scipy.ndimage import binary_fill_holes, distance_transform_edt, label

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
CONTAINER = os.path.join(ROOT, 'skins', 'neon', 'container')
# pre-holefill_v2 는 유저가 직접 편집한 버전 (left 복원, right 유저 편집) — 항상 이 상태에서 시작
BACKUP_DIR = os.path.join(ROOT, 'versions', 'sakura_tree_pre_holefill_v2')

SMALL_HOLE_MAX = 300  # 이 이하 pixel 만 inpaint, 큰 건 sky 로 유지

for name in ['left', 'right']:
    src = os.path.join(CONTAINER, f'sakura_tree_{name}.png')
    backup = os.path.join(BACKUP_DIR, f'sakura_tree_{name}.png')
    if not os.path.exists(backup):
        print(f'ERROR: backup missing: {backup}')
        continue

    img = Image.open(backup).convert('RGBA')  # 항상 백업에서 시작 (복구)
    arr = np.array(img)
    h, w = arr.shape[:2]
    print(f'\n{name}: {w}x{h}, backup size {os.path.getsize(backup)/1024:.0f} KB')

    a = arr[:, :, 3]
    mask = a > 50
    filled = binary_fill_holes(mask)
    holes = filled & ~mask
    # 홀 라벨링 + 크기 필터
    lbl, n_labels = label(holes)
    sizes = np.bincount(lbl.ravel())
    # 작은 홀만 True
    small_mask = np.zeros_like(holes, dtype=bool)
    small_count = 0
    small_px = 0
    for li in range(1, n_labels + 1):
        if sizes[li] <= SMALL_HOLE_MAX:
            small_mask |= (lbl == li)
            small_count += 1
            small_px += int(sizes[li])
    print(f'  total hole {n_labels}, {int(holes.sum())} px - small hole {small_count} ({small_px} px) inpaint')

    if small_mask.sum() > 0:
        # 가까운 opaque pixel 찾기 (원본 mask 기준)
        _, (iy, ix) = distance_transform_edt(~mask, return_indices=True)
        hy, hx = np.where(small_mask)
        src_y = iy[hy, hx]
        src_x = ix[hy, hx]
        arr[hy, hx, 0] = arr[src_y, src_x, 0]
        arr[hy, hx, 1] = arr[src_y, src_x, 1]
        arr[hy, hx, 2] = arr[src_y, src_x, 2]
        arr[hy, hx, 3] = arr[src_y, src_x, 3]

    # 알파 threshold (이전 작업에서 엣지 crisp)
    a_new = arr[:, :, 3].astype(np.int32)
    a_new = np.where(a_new < 40, 0, a_new)
    arr[:, :, 3] = a_new.astype(np.uint8)

    # 64 color quantize + compress
    img2 = Image.fromarray(arr, 'RGBA')
    r, g, b, aa = img2.split()
    rgb = Image.merge('RGB', (r, g, b))
    p = rgb.quantize(colors=64, method=2)
    rgb_q = p.convert('RGB')
    final = Image.merge('RGBA', (*rgb_q.split(), aa))
    final.save(src, optimize=True, compress_level=9)
    print(f'  saved: {os.path.getsize(src)/1024:.0f} KB')
