# -*- coding: utf-8 -*-
"""원본 mix vs Demucs drum stem onset 타이밍 비교."""
import sys, os, glob
import numpy as np, librosa
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
MUSIC = os.path.join(ROOT, 'Music')

SONGS = [
    ('봉인해제 Dragon', '봉인해제_Dragon'),
    ('ATLANTIS', 'Atlantis'),
    ('夢緣', '夢緣_(몽연)'),
    ('Cherry Blossom', 'Cherry Blossom'),
    ('Sugar Pixel', 'Sugar Pixel'),
    ('Lucifer', 'Lucifer'),
]


def detect_onsets(data, sr, sensitivity=1.1, min_gap_ms=30):
    win = max(1, int(sr * 0.015)); min_gap = int(sr * min_gap_ms / 1000)
    onsets = []; smoothed = 0.0; last = -min_gap * 2; n = len(data); i = 0
    while i < n:
        end = min(i + win, n)
        ch = data[i:end:8]; cnt = len(ch)
        e = float(np.sqrt(np.sum(ch * ch) / cnt)) if cnt else 0.0
        if e > 0.003 and e > smoothed * sensitivity and (i - last) > min_gap:
            onsets.append(i / sr); last = i
        smoothed = e * 0.2 + smoothed * 0.8
        i += win
    return onsets


def find_main(prefix):
    p = os.path.join(MUSIC, prefix + '.ogg')
    if os.path.exists(p): return p
    for f in os.listdir(MUSIC):
        if f.lower().endswith('.ogg') and prefix.lower().split('_')[0][:6] in f.lower():
            return os.path.join(MUSIC, f)
    return None


print('곡별 — 원본 mix 와 Demucs drum stem 의 onset 타이밍 비교')
print('drum onset 시각 - 원본 mix 가장 가까운 onset = offset')
print('-' * 90)

for display, prefix in SONGS:
    main_p = find_main(prefix)
    if not main_p:
        print('%-22s [메인 OGG 못 찾음]' % display); continue
    stem_dir = main_p[:-4] + '/'
    drum_p = None
    if os.path.isdir(stem_dir):
        c = glob.glob(os.path.join(stem_dir, '*_drums.ogg'))
        if c: drum_p = c[0]
    if not drum_p:
        print('%-22s [drum stem 못 찾음]' % display); continue

    try:
        d_main, sr1 = librosa.load(main_p, sr=22050, mono=True, duration=30.0)
        d_drum, sr2 = librosa.load(drum_p, sr=22050, mono=True, duration=30.0)
    except Exception as e:
        print('%-22s [load 실패: %s]' % (display, str(e)[:50])); continue

    ons_main = detect_onsets(d_main.astype(np.float64), sr1)
    ons_drum = detect_onsets(d_drum.astype(np.float64), sr2)
    if not ons_drum or not ons_main:
        print('%-22s [onset 없음: main=%d drum=%d]' % (display, len(ons_main), len(ons_drum))); continue

    # 각 drum onset 에 대해 main 의 가장 가까운 onset 찾기
    main_arr = np.array(ons_main)
    offsets = []
    for dt in ons_drum:
        idx = np.argmin(np.abs(main_arr - dt))
        diff = dt - main_arr[idx]
        if abs(diff) < 0.15:
            offsets.append(diff)

    if offsets:
        a = np.array(offsets)
        print('%-22s main=%-4d drum=%-4d matched=%-4d | drum-main: mean %+6.1fms  median %+6.1fms  std %5.1fms' % (
            display[:22], len(ons_main), len(ons_drum), len(offsets),
            a.mean() * 1000, np.median(a) * 1000, a.std() * 1000))
    else:
        print('%-22s [매칭 없음]' % display)
