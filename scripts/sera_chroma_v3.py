"""
세라 raw chroma key v3 — 피부톤 보존.
v2 → v3 차이: spill removal 을 외곽 anti-alias (0 < alpha < 1) 영역만 적용.
내부 (alpha=1) 는 RGB 완전 보존 → 피부톤 안 바뀜.
"""
import os
import sys
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

    LO, HI = 20.0, 80.0
    alpha_mask = np.clip(1.0 - (green_excess - LO) / (HI - LO), 0.0, 1.0)
    alpha_mask = np.where(luminance < 80, 1.0, alpha_mask)
    alpha_mask = np.where(green_excess <= 0, 1.0, alpha_mask)

    # spill removal: 외곽 (0 < alpha < 1) 만. 내부 alpha=1 영역 (피부/옷 등) 보존
    edge = (alpha_mask > 0) & (alpha_mask < 1)
    spill = np.clip(green_excess, 0, None)
    g_new = np.where(edge, np.maximum(rb_max, g - spill * 0.8), g)

    out = arr.copy()
    out[:, :, 1] = g_new
    out[:, :, 3] = np.clip(arr[:, :, 3] * alpha_mask, 0, 255)
    out = np.clip(out, 0, 255).astype(np.uint8)
    Image.fromarray(out, 'RGBA').save(out_path)
    print(f'{in_name} -> {out_name}')


if __name__ == '__main__':
    if len(sys.argv) >= 3:
        pairs = [(sys.argv[i], sys.argv[i + 1]) for i in range(1, len(sys.argv), 2)]
    else:
        pairs = [('1.png', 'miss_idle.png')]
    for src, dst in pairs:
        remove_chroma(src, dst)
