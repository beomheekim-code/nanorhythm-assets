# -*- coding: utf-8 -*-
"""
꽃 모양 노트/홀드머리 재분석:
1. 배경 투명화 (max(R,G,B)<35)
2. 각 셀 타이트 bbox (꽃 실루엣 경계)
3. 셀별 중앙 RGB 샘플 (팔레트 확인)
"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from PIL import Image
import numpy as np

BASE = 'D:/리듬게임/skins/neon/note'

def analyze(name, n_cells=8):
    path = os.path.join(BASE, name)
    im = Image.open(path).convert('RGBA')
    a = np.array(im)
    H, W = a.shape[:2]
    # 투명화
    rgb = a[:, :, :3]
    max_ch = rgb.max(axis=2)
    a[max_ch < 35, 3] = 0
    # 셀 분할
    cw = W / n_cells
    alpha = a[:, :, 3]
    cells = []
    for i in range(n_cells):
        x0 = int(round(i * cw))
        x1 = int(round((i + 1) * cw))
        slab = alpha[:, x0:x1]
        cx = np.where(slab.max(axis=0) > 0)[0]
        ry = np.where(slab.max(axis=1) > 0)[0]
        if len(cx) == 0 or len(ry) == 0:
            cells.append(None); continue
        bx = x0 + int(cx[0])
        by = int(ry[0])
        bw = int(cx[-1] - cx[0] + 1)
        bh = int(ry[-1] - ry[0] + 1)
        cells.append((bx, by, bw, bh))
    # 저장
    Image.fromarray(a).save(path)
    # 센터 샘플
    samples = []
    for c in cells:
        if c is None:
            samples.append(None); continue
        cx = c[0] + c[2] // 2
        cy = c[1] + c[3] // 2
        r, g, b, al = a[cy, cx]
        samples.append((f'#{r:02x}{g:02x}{b:02x}', al))
    print(f'{name}  size={W}x{H}')
    for i, (c, s) in enumerate(zip(cells, samples)):
        print(f'  [{i}] bbox={c}  center={s}')
    return cells

print('=== 새 꽃 sprite 분석 ===\n')
note_cells   = analyze('벚꽃_노트.png')
head_cells   = analyze('벚꽃_홀드머리.png')

# SKINS 용 공통 aspect (꽃 크기 평균) 계산
def avg_aspect(cells):
    ws = [c[2] for c in cells if c]
    hs = [c[3] for c in cells if c]
    return sum(hs)/len(hs) / (sum(ws)/len(ws))

print(f'\n note aspect (h/w avg): {avg_aspect(note_cells):.3f}')
print(f' head aspect (h/w avg): {avg_aspect(head_cells):.3f}')
