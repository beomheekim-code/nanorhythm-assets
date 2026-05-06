"""
세라 피부 빨강 보정.
대상: alpha=255 인 내부 영역 중 피부톤 (r > g+5, r > b, r > 150, lum > 100)
- r 채널 -8 (빨강 줄임)
검정 lineart / 머리 / 옷 / 외곽 anti-alias 영역 보호.
"""
import os
import sys
from PIL import Image
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERA_DIR = os.path.join(BASE, 'skins', 'bj_sera')


def fix_skin(name, r_offset=-8):
    p = os.path.join(SERA_DIR, name)
    img = Image.open(p).convert('RGBA')
    arr = np.array(img, dtype=np.float32)
    r, g, b, a = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2], arr[:, :, 3]
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    skin = (a == 255) & (r > g + 5) & (r > b) & (lum > 100) & (r > 150)
    r_new = np.where(skin, np.clip(r + r_offset, 0, 255), r)
    arr[:, :, 0] = r_new
    out = np.clip(arr, 0, 255).astype(np.uint8)
    Image.fromarray(out, 'RGBA').save(p)
    print(f'{name}: skin px {int(skin.sum())} adjusted r{r_offset:+d}')


if __name__ == '__main__':
    targets = sys.argv[1:] if len(sys.argv) > 1 else [
        'strike_far_fever_1.png',
        'strike_idle_fever_1.png',
        'strike_near_fever_1.png',
        'miss_fever.png',
    ]
    for n in targets:
        fix_skin(n)
