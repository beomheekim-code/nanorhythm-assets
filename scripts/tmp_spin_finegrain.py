# -*- coding: utf-8 -*-
"""SPIN 28-42s 1초 단위로 mix-onset 분포 — 진짜 어디 sparse 한지."""
import os, sys
import numpy as np, librosa
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
MUSIC = os.path.join(ROOT, 'Music', 'Spin')
STEM_NAMES = ['drums', 'bass', 'vocals', 'instrum', 'piano', 'guitar', 'other']
EXCLUDE = [4]


def detect_onsets(data, sr, sens=1.05, min_gap_ms=30):
    win = max(1, int(sr * 0.015))
    min_gap = int(sr * min_gap_ms / 1000)
    onsets = []
    smoothed = 0.0
    last = -min_gap * 2
    n = len(data)
    i = 0
    while i < n:
        end = min(i + win, n)
        ch = data[i:end:8]
        cnt = len(ch)
        e = float(np.sqrt(np.sum(ch * ch) / cnt)) if cnt else 0.0
        if e > 0.003 and e > smoothed * sens and (i - last) > min_gap:
            onsets.append(i / sr)
            last = i
        smoothed = e * 0.2 + smoothed * 0.8
        i += win
    return onsets


stems = {}
sr = None
for i, sn in enumerate(STEM_NAMES):
    if i in EXCLUDE:
        continue
    p = os.path.join(MUSIC, 'Spin_%s.ogg' % sn)
    if not os.path.exists(p):
        continue
    d, _sr = librosa.load(p, sr=22050, mono=True)
    stems[i] = d
    sr = _sr

mxlen = max(len(d) for d in stems.values())
sumbuf = np.zeros(mxlen, dtype=np.float64)
for d in stems.values():
    sumbuf[:len(d)] += d

mix_onsets = detect_onsets(sumbuf, sr)
drum_onsets = detect_onsets(stems[0], sr)

# 0.5s 단위로 mix onset 수 + 전체 stem onset 수 + sum RMS
print('=== SPIN 28-42s 0.5초 단위 분포 ===\n')
print('%-7s %-5s %-6s %-7s %-7s' % ('time', 'mix', 'drums', 'sumRMS', 'note?'))
for bs in np.arange(28.0, 42.0, 0.5):
    mix_c = sum(1 for t in mix_onsets if bs <= t < bs + 0.5)
    drum_c = sum(1 for t in drum_onsets if bs <= t < bs + 0.5)
    s_idx, e_idx = int(bs * sr), int((bs + 0.5) * sr)
    rms = float(np.sqrt(np.mean(sumbuf[s_idx:e_idx] ** 2)))
    bar = '#' * mix_c
    print('%5.1fs  %2d    %2d    %.4f  %s' % (bs, mix_c, drum_c, rms, bar))

# 28-42s 전체 stem 별 분포
print('\n=== 28-42s stem 별 onset 분포 ===')
for si in sorted(stems.keys()):
    cnt = sum(1 for t in detect_onsets(stems[si], sr) if 28 <= t <= 42)
    print('  stem %d (%-7s): %d개' % (si, STEM_NAMES[si], cnt))
