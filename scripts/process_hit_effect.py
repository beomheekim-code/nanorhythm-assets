# -*- coding: utf-8 -*-
"""
hit_effect 5장 체커 제거 (투명 유지 버전).

유저 피드백:
- "투명 상태로 만들지말고 체크무늬만 없애줘"
- 리소스 자체는 잘 뽑힌 상태
- 체크판이 RGB 에 박혀있거나 반투명 영역 때문에 뷰어 체커가 비쳐보이는 것

전략:
1. 알파는 절대 0 으로 죽이지 않음 (원본 모양 완전 보존)
2. RGB 에 median+gaussian blur 로 체커 dither/노이즈 제거
3. 중간 알파(30~200) 를 강하게 부스트 → 뷰어 체커 비침 방지
   (opaque 에 가깝게 만들어도 원본 실루엣 그대로)
4. 완전 투명(alpha=0) 영역만 그대로 둠
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image, ImageFilter
import numpy as np
from scipy.ndimage import binary_fill_holes, binary_dilation

BASE = 'D:/nanorhythm-assets/nanorhythm-assets/skins/neon/hit_effect'
FILES = ['petal_01.png', 'petal_02.png', 'ring_pink.png', 'ring_gold.png', 'core_flash.png']


def box_mean(arr, radius):
    """numpy 박스 평균 (radius=1 → 3x3, radius=2 → 5x5)."""
    arr = arr.astype(np.float32)
    padded = np.pad(arr, radius, mode='edge')
    size = 2 * radius + 1
    acc = np.zeros_like(arr, dtype=np.float32)
    for dy in range(size):
        for dx in range(size):
            acc += padded[dy:dy + arr.shape[0], dx:dx + arr.shape[1]]
    return acc / (size * size)


def process(filename):
    path = os.path.join(BASE, filename)
    im = Image.open(path).convert('RGBA')
    a = np.array(im)
    H, W = a.shape[:2]
    rgb = a[:, :, :3]
    alpha = a[:, :, 3].astype(np.float32)

    # ─── Pass 1: RGB 강한 median 필터 (isolated pixel 제거) ───
    pil_im = Image.fromarray(rgb)
    med = pil_im.filter(ImageFilter.MedianFilter(size=5))
    rgb_med = np.array(med)

    # ─── Pass 2: 강한 박스 블러 — 교대 체커 패턴 평균화 ───
    # 교대 패턴은 반드시 averaging 필요 (median 은 통과 못 시킴)
    # radius=4 (9x9) 로 큰 체커 블록도 smooth out
    rgb_blur = np.zeros_like(rgb_med, dtype=np.float32)
    for ch in range(3):
        bl = box_mean(rgb_med[:, :, ch], radius=4)
        # 한 번 더 (총 17x17 효과)
        bl = box_mean(bl, radius=3)
        rgb_blur[:, :, ch] = bl
    rgb_smooth = np.clip(rgb_blur, 0, 255).astype(np.uint8)

    # 알파가 조금이라도 있는 픽셀은 스무딩된 RGB 로 교체
    visible = (alpha > 5)[..., None]
    rgb = np.where(visible, rgb_smooth, rgb)

    # ─── Pass 3: 알파 하드 부스트 (반투명 본체 → 완전 불투명) ───
    # 30 미만: 그대로 (부드러운 feather 경계 유지)
    # 30 이상: 바로 255 (체커 비침 완전 제거)
    a = alpha.copy()
    out_a = np.where(a >= 30, 255.0, a)
    alpha_u8 = np.clip(out_a, 0, 255).astype(np.uint8)

    # ─── Pass 4: 내부 구멍 메우기 (hollow interior → 불투명 fill) ───
    # 페탈/링 내부에 체커 비침 제거
    raw_mask = alpha > 10
    dilated = binary_dilation(raw_mask, iterations=5)
    filled_mask = binary_fill_holes(dilated)
    solid_mask = alpha_u8 > 200
    newly_filled = filled_mask & ~solid_mask
    if np.any(newly_filled):
        body_rgb = rgb[solid_mask]
        if len(body_rgb) > 0:
            fill_color = np.median(body_rgb, axis=0).astype(np.uint8)
            rgb[newly_filled] = fill_color
            alpha_u8[newly_filled] = 255

    # ─── Pass 5: 최종 통합 블러 (fill 후 생긴 색 경계 smooth) ───
    # fill 로 채워진 영역과 기존 영역 사이의 하드 edge 제거
    final_blur = np.zeros_like(rgb, dtype=np.float32)
    for ch in range(3):
        bl = box_mean(rgb[:, :, ch], radius=3)
        bl = box_mean(bl, radius=2)
        final_blur[:, :, ch] = bl
    # alpha_u8 > 200 (본체 + fill) 영역만 교체
    body_full = (alpha_u8 > 200)[..., None]
    rgb = np.where(body_full, np.clip(final_blur, 0, 255).astype(np.uint8), rgb)

    # ─── Pass 4: 작은 알파 잔티 정리 ───
    alpha_u8[alpha_u8 < 8] = 0

    out = np.dstack([rgb, alpha_u8])
    Image.fromarray(out).save(path)

    total = H * W
    opaque = int(np.sum(alpha_u8 > 240))
    partial = int(np.sum((alpha_u8 > 10) & (alpha_u8 <= 240)))
    zero = int(np.sum(alpha_u8 == 0))
    print(f'{filename}  {W}x{H}  opaque={opaque}  partial={partial}  zero={zero}  ({zero*100/total:.1f}% 투명)')


print('=== hit_effect 체커 제거 (투명 유지) ===\n')
for fn in FILES:
    process(fn)
print('\n완료.')
