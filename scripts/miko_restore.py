"""
miko_taiko 복구 스크립트.
- 원본.png 에서 12 셀 재추출
- 라벨 텍스트 (좌상단 작은 검은 글자) 만 connected-component 로 정밀 제거
- chroma green 제거 + Edge Extension
- right = left 복사 (단순 flip 안 함 — 캐릭터 방향 바뀌므로)
  유저가 진짜 우측 자세 PNG 별도 생성 필요 또는 코드 squash 애니로 대체
"""
import os
import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, distance_transform_edt, label

DIR = r'D:\nanorhythm-assets\nanorhythm-assets\skins\miko_taiko'
SRC = os.path.join(DIR, '원본.png')

# 시트 12 cells (4 cols × 3 rows) → mode_col 매핑
# r1=normal r2=fever r3=miss
# c1=idle (raise) c2=hit  c3=같은 자세  c4=같은 자세
NAME_MAP = {
    (1,1): 'idle_left',
    (1,2): 'hit_left',
    (2,1): 'idle_fever_left',
    (2,2): 'hit_fever_left',
    (3,1): 'miss_idle_left',
    (3,2): 'miss_left',
}

def remove_top_left_labels_post(arr):
    """chroma cleanup 후 적용 — 좌상단 영역 내 작은 isolated CC (라벨) 제거.
    캐릭터 본체는 큰 CC 라 영향 없음."""
    h, w = arr.shape[:2]
    a = arr[:,:,3]
    mask = a > 50
    lab, n = label(mask)
    if n == 0: return arr
    sizes = np.bincount(lab.ravel()); sizes[0] = 0
    # 각 CC 의 bbox 측정
    for ci in range(1, n + 1):
        if sizes[ci] > 5000:  # 캐릭터 본체 (큰 CC) 보호
            continue
        ys, xs = np.where(lab == ci)
        if len(ys) == 0: continue
        y_min, y_max = ys.min(), ys.max()
        x_min, x_max = xs.min(), xs.max()
        # CC 가 전체적으로 좌상단 영역 안 (y < 60 AND x < 100) 에 있으면 라벨
        if y_max < 60 and x_max < 100:
            arr[lab == ci, 3] = 0
    return arr

def cleanup_chroma(arr):
    arr = arr.copy().astype(np.int16)
    r, g, b, a = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]

    # 1. chroma alpha kill — 원본 green 기준 (spill 전에)
    g_excess_orig = np.maximum(0, g - np.maximum(r, b))
    alpha_mul = np.clip(1 - g_excess_orig / 60.0, 0, 1) ** 1.2
    new_a = (a * alpha_mul).astype(np.int16)
    new_a = np.where(new_a < 25, 0, new_a)
    arr[:,:,3] = new_a
    a = arr[:,:,3]

    # 2. spill suppression on remaining opaque pixels
    spill = (g > np.maximum(r, b)) & (a > 0)
    arr[:,:,1] = np.where(spill, np.maximum(r, b), g)
    g = arr[:,:,1]

    # 3. dust + core 외 fuzz 제거
    mask = a > 50
    lab, n = label(mask)
    if n > 0:
        sizes = np.bincount(lab.ravel()); sizes[0] = 0
        keep = sizes > 200  # 큰 cc (캐릭터 본체) 만
        keep_mask = keep[lab]
        arr[mask & ~keep_mask, 3] = 0
        a = arr[:,:,3]

    core = a > 200
    soft = binary_dilation(core, iterations=4)
    arr[~soft & (a > 0), 3] = 0
    a = arr[:,:,3]

    # 4. halo
    halo = (a > 0) & (a < 30)
    arr[halo, 3] = 0

    # 5. Edge Extension
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

# 원본 12셀 분할
src = Image.open(SRC).convert('RGBA')
W, H = src.size
COLS, ROWS = 4, 3
cw, ch = W // COLS, H // ROWS
print(f'sheet {W}x{H}, cell {cw}x{ch}\n')

for (row, col), name in NAME_MAP.items():
    cell = src.crop(((col-1)*cw, (row-1)*ch, col*cw, row*ch))
    arr = np.array(cell)
    # 1. chroma cleanup + edge ext
    cleaned = cleanup_chroma(arr)
    # 2. chroma 후 좌상단 isolated CC (라벨) 제거 — 캐릭터 본체 영향 X
    cleaned = remove_top_left_labels_post(cleaned)
    # Edge Extension 다시 (라벨 자리도 transparent 처리)
    a2 = cleaned[:,:,3]
    opaque = a2 > 0
    if opaque.any():
        _, idx = distance_transform_edt(~opaque, return_distances=True, return_indices=True)
        ny, nx = idx[0], idx[1]
        transparent = ~opaque
        cleaned[transparent, 0] = cleaned[ny[transparent], nx[transparent], 0]
        cleaned[transparent, 1] = cleaned[ny[transparent], nx[transparent], 1]
        cleaned[transparent, 2] = cleaned[ny[transparent], nx[transparent], 2]
    out_l = os.path.join(DIR, f'{name}.png')
    Image.fromarray(cleaned, 'RGBA').save(out_l, optimize=True, compress_level=9)
    # right = 일단 left 복사 (유저가 별도로 우측 자세 생성 필요)
    out_r = out_l.replace('_left.png', '_right.png')
    Image.fromarray(cleaned, 'RGBA').save(out_r, optimize=True, compress_level=9)
    print(f'r{row}c{col} → {name}.png + {os.path.basename(out_r)} ({os.path.getsize(out_l)/1024:.0f} KB)')

print('\nDone. *_right.png 는 일단 left 복사본 — 진짜 우측 자세는 Gemini 추가 생성 필요.')
