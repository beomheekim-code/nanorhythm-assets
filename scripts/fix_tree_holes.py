"""
sakura_tree_left/right 의 트렁크 내부 투명 홀 (빵꾸) 을 주변 나무색으로 inpaint.

알고리즘:
1. alpha > 50 = opaque mask
2. binary_fill_holes → 트리 실루엣 전체 (외부 투명 + 내부 홀 포함 → True)
3. filled & ~mask = 내부 홀만 True
4. 각 홀 픽셀에 대해 distance_transform_edt 로 가장 가까운 opaque 픽셀 index 얻음
5. 그 opaque 픽셀의 RGB 를 홀 픽셀에 복사
6. 홀 픽셀의 alpha 를 주변 평균 alpha 로 (opaque)
7. PIL 로 optimize + compress 저장

백업: versions/sakura_tree_raw/ 에 left/right 둘 다.
"""
import os
import shutil
import numpy as np
from PIL import Image
from scipy.ndimage import binary_fill_holes, distance_transform_edt

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
CONTAINER = os.path.join(ROOT, 'skins', 'neon', 'container')
BACKUP_DIR = os.path.join(ROOT, 'versions', 'sakura_tree_pre_holefill_v2')
os.makedirs(BACKUP_DIR, exist_ok=True)

for name in ['left', 'right']:
    src = os.path.join(CONTAINER, f'sakura_tree_{name}.png')
    backup = os.path.join(BACKUP_DIR, f'sakura_tree_{name}.png')
    if not os.path.exists(backup):
        shutil.copy(src, backup)
        print(f'backup: {backup}')

    img = Image.open(src).convert('RGBA')
    arr = np.array(img)
    h, w = arr.shape[:2]
    print(f'\n{name}: {w}x{h}, orig size {os.path.getsize(src)/1024:.0f} KB')

    a = arr[:, :, 3]
    mask = a > 50
    filled = binary_fill_holes(mask)
    holes = filled & ~mask
    n_holes = int(holes.sum())
    print(f'  내부 홀 pixel: {n_holes}')

    if n_holes > 0:
        # 가까운 opaque pixel 의 index
        _, (iy, ix) = distance_transform_edt(~mask, return_indices=True)
        # 홀 픽셀 대상으로만 RGB 복사
        hy, hx = np.where(holes)
        src_y = iy[hy, hx]
        src_x = ix[hy, hx]
        arr[hy, hx, 0] = arr[src_y, src_x, 0]
        arr[hy, hx, 1] = arr[src_y, src_x, 1]
        arr[hy, hx, 2] = arr[src_y, src_x, 2]
        arr[hy, hx, 3] = arr[src_y, src_x, 3]
        print(f'  홀 {n_holes} pixel → 주변 opaque 색으로 inpaint')

    # 알파 threshold (깔끔한 엣지)
    a_new = arr[:, :, 3].astype(np.int32)
    a_new = np.where(a_new < 40, 0, a_new)
    arr[:, :, 3] = a_new.astype(np.uint8)

    # 48-color quantize + compress (기존 워크플로와 동일)
    img2 = Image.fromarray(arr, 'RGBA')
    r, g, b, aa = img2.split()
    rgb = Image.merge('RGB', (r, g, b))
    p = rgb.quantize(colors=64, method=2)  # 나무 부드러운 그라데이션 위해 64
    rgb_q = p.convert('RGB')
    final = Image.merge('RGBA', (*rgb_q.split(), aa))
    final.save(src, optimize=True, compress_level=9)
    print(f'  saved: {os.path.getsize(src)/1024:.0f} KB')
