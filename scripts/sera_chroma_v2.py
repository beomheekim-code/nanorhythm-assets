"""
세라 raw chroma key 정밀 처리.
- 검정 lineart 보호: luminance < 80 인 픽셀 완전 보존
- soft alpha: green_excess 점진적 → 외곽선 anti-alias 자연
- spill removal: 초록 영향 줄어든 g 값
"""
import os
from PIL import Image
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERA_DIR = os.path.join(BASE, 'skins', 'bj_sera')

def remove_chroma(in_name, out_name):
    in_path = os.path.join(SERA_DIR, in_name)
    out_path = os.path.join(SERA_DIR, out_name)
    img = Image.open(in_path).convert('RGBA')
    arr = np.array(img, dtype=np.float32)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]

    rb_max = np.maximum(r, b)
    green_excess = g - rb_max
    luminance = 0.299 * r + 0.587 * g + 0.114 * b

    # alpha: green_excess (px) 0~80 -> 1.0~0.0
    LO, HI = 20.0, 80.0
    alpha_mask = np.clip(1.0 - (green_excess - LO) / (HI - LO), 0.0, 1.0)
    # 검정 lineart 완전 보존
    alpha_mask = np.where(luminance < 80, 1.0, alpha_mask)
    # 초록 우세 X 영역 보존
    alpha_mask = np.where(green_excess <= 0, 1.0, alpha_mask)

    # spill removal: green excess > 10 인 곳에서만 g 줄임
    spill = np.clip(green_excess, 0, None)
    g_new = np.where(green_excess > 10, np.maximum(rb_max, g - spill * 0.8), g)

    out = arr.copy()
    out[:, :, 1] = g_new
    out[:, :, 3] = np.clip(arr[:, :, 3] * alpha_mask, 0, 255)
    out = np.clip(out, 0, 255).astype(np.uint8)
    Image.fromarray(out, 'RGBA').save(out_path)
    print(f'{in_name} -> {out_name}')


MAPPING = [
    ('1.png', 'miss_fever.png'),
    ('2.png', 'strike_far_fever_1.png'),
    ('3.png', 'strike_idle_fever_1.png'),
    ('4.png', 'strike_near_fever_1.png'),
]

for src, dst in MAPPING:
    remove_chroma(src, dst)
