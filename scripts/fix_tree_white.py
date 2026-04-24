"""
sakura_tree 의 흰색 얼룩을 주변 non-white 색으로 교체.

원본 Gemini 이미지가 trunk 에 강한 흰색 하이라이트를 넣어서
유저가 "나무색이 하얗게 된 부분" 으로 인지.

알고리즘:
1. mask_white = R,G,B 모두 195+ AND alpha > 50 (밝은 흰색 계열)
2. 각 white pixel 에 대해 distance_transform_edt 로 가장 가까운 non-white opaque pixel RGB 복사
3. alpha 는 유지

trunk 의 흰색 → 가까운 brown 으로 교체
꽃 근처 흰색 → 가까운 pink 로 교체 (자연)

백업: pre_holefill_v2 와 별도로 pre_white_v1 에 저장.
"""
import os
import shutil
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
CONTAINER = os.path.join(ROOT, 'skins', 'neon', 'container')
BACKUP_DIR = os.path.join(ROOT, 'versions', 'sakura_tree_pre_white_v1')
os.makedirs(BACKUP_DIR, exist_ok=True)

WHITE_FLOOR = 195

for name in ['left', 'right']:
    src = os.path.join(CONTAINER, f'sakura_tree_{name}.png')
    backup = os.path.join(BACKUP_DIR, f'sakura_tree_{name}.png')
    if not os.path.exists(backup):
        shutil.copy(src, backup)
        print(f'backup: {backup}')

    img = Image.open(src).convert('RGBA')
    arr = np.array(img)
    h, w = arr.shape[:2]
    print(f'\n{name}: {w}x{h}, orig {os.path.getsize(src)/1024:.0f} KB')

    a = arr[:, :, 3]
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    # 흰색 계열
    white = (r >= WHITE_FLOOR) & (g >= WHITE_FLOOR) & (b >= WHITE_FLOOR) & (a > 50)
    n_white = int(white.sum())
    # non-white opaque (교체 소스)
    non_white_opaque = (~white) & (a > 50)
    print(f'  white: {n_white} px, non-white opaque: {int(non_white_opaque.sum())} px')

    if n_white > 0 and non_white_opaque.any():
        # 각 pixel 에 대해 가장 가까운 non-white-opaque index
        _, (iy, ix) = distance_transform_edt(~non_white_opaque, return_indices=True)
        wy, wx = np.where(white)
        src_y = iy[wy, wx]
        src_x = ix[wy, wx]
        arr[wy, wx, 0] = arr[src_y, src_x, 0]
        arr[wy, wx, 1] = arr[src_y, src_x, 1]
        arr[wy, wx, 2] = arr[src_y, src_x, 2]
        # alpha 유지
        print(f'  replaced {n_white} white px with nearest non-white color')

    # quantize — 128 컬러로 올려서 색 손실 줄임
    img2 = Image.fromarray(arr, 'RGBA')
    rc, gc, bc, ac = img2.split()
    rgb = Image.merge('RGB', (rc, gc, bc))
    p = rgb.quantize(colors=128, method=2)
    rgb_q = p.convert('RGB')
    final = Image.merge('RGBA', (*rgb_q.split(), ac))
    final.save(src, optimize=True, compress_level=9)
    print(f'  saved: {os.path.getsize(src)/1024:.0f} KB')
