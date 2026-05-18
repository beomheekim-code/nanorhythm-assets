# -*- coding: utf-8 -*-
"""SPIN 30-40s 의 0.5s 버킷별 MUSICAL stem RMS — ambient filter 통과 여부 확인."""
import os, sys
import numpy as np, librosa
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
MUSIC = os.path.join(ROOT, 'Music', 'Spin')
STEM_NAMES = ['drums', 'bass', 'vocals', 'instrum', 'piano', 'guitar', 'other']
MUSICAL = [0, 1, 3, 4, 5]  # drums, bass, instrum, piano, guitar (index)
ABS_FLOOR = 0.02
BUCKET = 0.5

stems = {}
sr = None
for i, sn in enumerate(STEM_NAMES):
    p = os.path.join(MUSIC, 'Spin_%s.ogg' % sn)
    if not os.path.exists(p):
        print('  [없음] stem %d (%s)' % (i, sn))
        continue
    d, _sr = librosa.load(p, sr=22050, mono=True)
    stems[i] = d
    sr = _sr

# 30-40s 의 0.5s 버킷별 RMS
print('=== SPIN 30-40s 0.5s 버킷별 MUSICAL stem RMS (ABS_FLOOR=0.02) ===\n')
print('%-7s %-7s %-7s %-7s %-7s %-7s %-7s %s' % ('time', 'drums', 'bass', 'instr', 'piano', 'guitar', 'max', 'PASS?'))
for bs in np.arange(28.0, 42.0, BUCKET):
    s_idx, e_idx = int(bs * sr), int((bs + BUCKET) * sr)
    row = []
    max_rms = 0
    for si in MUSICAL:
        if si not in stems:
            row.append(0)
            continue
        chunk = stems[si][s_idx:e_idx]
        rms = float(np.sqrt(np.mean(chunk * chunk))) if len(chunk) > 0 else 0
        row.append(rms)
        if rms > max_rms:
            max_rms = rms
    passes = 'PASS' if max_rms > ABS_FLOOR else '*** DROP ***'
    print('%5.1fs  %.4f  %.4f  %.4f  %.4f  %.4f  %.4f  %s' % (
        bs, row[0], row[1], row[2], row[3], row[4], max_rms, passes))

# 같이 보컬도 표시
print('\n=== 같은 구간 vocals + other RMS (참고) ===')
for bs in np.arange(28.0, 42.0, BUCKET):
    s_idx, e_idx = int(bs * sr), int((bs + BUCKET) * sr)
    v = stems.get(2)
    o = stems.get(6)
    vrms = float(np.sqrt(np.mean(v[s_idx:e_idx] ** 2))) if v is not None else 0
    orms = float(np.sqrt(np.mean(o[s_idx:e_idx] ** 2))) if o is not None else 0
    print('  %5.1fs  vocals %.4f  other %.4f' % (bs, vrms, orms))
