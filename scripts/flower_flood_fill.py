# -*- coding: utf-8 -*-
"""
꽃 sprite 배경 투명화 — cell 코너에서 flood fill 로 연결된 dark sky 만 제거.
threshold 기반 단순 방식은 꽃 내부 dark antialiasing 픽셀까지 투명화하거나
반대로 어두운 sky 가 남아서 지저분함. flood fill 이 정확함.

각 셀 (W/8 분할) 마다:
- 4 코너에서 시작
- pixel max(R,G,B) < THRESH 인 연결 컴포넌트 BFS
- 해당 픽셀들만 alpha=0
"""
import sys, io, os
from collections import deque
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image
import numpy as np

BASE = 'D:/리듬게임/skins/neon/note'
THRESH = 80  # 충분히 높게 — sky gradient 포함, 꽃 내부는 max>100 이라 안전

def flood_clear(name, n_cells=8):
    path = os.path.join(BASE, name)
    im = Image.open(path).convert('RGBA')
    a = np.array(im)
    H, W = a.shape[:2]
    rgb = a[:, :, :3]
    max_ch = rgb.max(axis=2)
    dark = max_ch < THRESH  # sky 후보

    # alpha 채널 초기화 (기존 transparent 유지)
    # 각 cell 마다 4 코너에서 flood fill
    cw = W / n_cells
    to_transparent = np.zeros((H, W), dtype=bool)

    for i in range(n_cells):
        x0 = int(round(i * cw))
        x1 = int(round((i + 1) * cw)) - 1
        corners = [(x0, 0), (x1, 0), (x0, H - 1), (x1, H - 1)]
        for (cx, cy) in corners:
            if not dark[cy, cx] or to_transparent[cy, cx]:
                continue
            # BFS flood
            q = deque([(cx, cy)])
            to_transparent[cy, cx] = True
            while q:
                x, y = q.popleft()
                for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx, ny = x+dx, y+dy
                    if x0 <= nx <= x1 and 0 <= ny < H:
                        if dark[ny, nx] and not to_transparent[ny, nx]:
                            to_transparent[ny, nx] = True
                            q.append((nx, ny))

    a[to_transparent, 3] = 0
    Image.fromarray(a).save(path)
    cleared = to_transparent.sum()
    total = H * W
    print(f'{name}: flood cleared {cleared} / {total} ({cleared/total*100:.1f}%)')

flood_clear('벚꽃_노트.png')
flood_clear('벚꽃_홀드머리.png')
