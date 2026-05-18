# -*- coding: utf-8 -*-
"""SPIN 30~40초 구간 정밀 진단 — stem 별 onset, slot filter 후 분포."""
import os, sys
import numpy as np, librosa
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
MUSIC = os.path.join(ROOT, 'Music', 'Spin')
PREFIX = 'Spin'
EXCLUDE = [4]
STEM_NAMES = ['drums', 'bass', 'vocals', 'instrum', 'piano', 'guitar', 'other']
BPM = 78
SLOT_SUBDIV = 0.5
SLOT_STEM_PRIO = [3, 6, 0, 1, 2]  # instrum, other, drums, bass, vocals


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
            onsets.append((i / sr, e))
            last = i
        smoothed = e * 0.2 + smoothed * 0.8
        i += win
    return onsets


# 로드
stems = {}
sr = None
for i, sn in enumerate(STEM_NAMES):
    if i in EXCLUDE:
        continue
    p = os.path.join(MUSIC, '%s_%s.ogg' % (PREFIX, sn))
    if not os.path.exists(p):
        continue
    d, _sr = librosa.load(p, sr=22050, mono=True)
    stems[i] = d
    sr = _sr

# mix 합
mxlen = max(len(d) for d in stems.values())
sumbuf = np.zeros(mxlen, dtype=np.float64)
for d in stems.values():
    sumbuf[:len(d)] += d

mix_onsets = detect_onsets(sumbuf, sr)
per_stem = {i: detect_onsets(stems[i], sr) for i in stems}

# 30-40초 구간만
T_START, T_END = 30.0, 40.0
def in_win(o): return T_START <= o[0] <= T_END

print('=== SPIN 30-40s 정밀 분석 ===\n')

# stem 별 onset 수
print('--- per-stem onsets in 30-40s ---')
for si in sorted(per_stem.keys()):
    ws = [o for o in per_stem[si] if in_win(o)]
    print('  stem %d (%s): %d개' % (si, STEM_NAMES[si], len(ws)))

# mix onsets
mix_in_win = [o for o in mix_onsets if in_win(o)]
print('\nmix onsets in 30-40s: %d' % len(mix_in_win))

# dominant stem 분포 (JS 코드와 동일 로직)
print('\n--- mix-onset 의 dominant stem 분포 (±25ms window) ---')
stem_count = {i: 0 for i in stems}
win_samples = int(sr * 0.025)
mix_assigned = []
for t, _e in mix_in_win:
    idx = int(t * sr)
    best_si, best_e = -1, -1
    for si in stems:
        d = stems[si]
        f, e = max(0, idx - win_samples), min(len(d), idx + win_samples)
        chunk = d[f:e]
        en = float(np.sum(chunk * chunk))
        if en > best_e:
            best_e = en
            best_si = si
    if best_si >= 0:
        stem_count[best_si] += 1
        mix_assigned.append((t, best_si, best_e))
for si in sorted(stem_count.keys()):
    print('  stem %d (%s): %d개' % (si, STEM_NAMES[si], stem_count[si]))

# slot filter 시뮬 — slot=sixteenth*0.5 (SPIN slotSubdivision=0.5)
beat = 60.0 / BPM
sixteenth = beat / 4
slot = sixteenth * 0.5  # 24ms for SPIN
print('\n  --- slot filter (slot=%.3fs, prio=%s) ---' % (slot, SLOT_STEM_PRIO))

def prio_of(si):
    if si in SLOT_STEM_PRIO:
        return len(SLOT_STEM_PRIO) - SLOT_STEM_PRIO.index(si)
    return 0

# mix_assigned 시간순 정렬
mix_assigned.sort(key=lambda x: x[0])
# 슬롯 단위로 best 픽
filtered = []
s_start = mix_assigned[0][0] if mix_assigned else T_START
nsidx = 0
while s_start < (mix_assigned[-1][0] if mix_assigned else T_END) + slot:
    s_end = s_start + slot
    best = None
    best_score = -1
    while nsidx < len(mix_assigned) and mix_assigned[nsidx][0] < s_end:
        t, si, e = mix_assigned[nsidx]
        if t >= s_start:
            p = prio_of(si)
            # priority 우선, 동률이면 energy
            score = p * 1e10 + e
            if score > best_score:
                best = (t, si, e)
                best_score = score
        nsidx += 1
    if best:
        filtered.append(best)
    s_start = s_end

print('  slot filter 통과: %d개 (mix_assigned %d 중)' % (len(filtered), len(mix_assigned)))

# 통과한 stem 분포
post_stem_count = {i: 0 for i in stems}
for t, si, e in filtered:
    post_stem_count[si] += 1
print('  --- 통과 후 stem 분포 ---')
for si in sorted(post_stem_count.keys()):
    print('  stem %d (%s): %d개' % (si, STEM_NAMES[si], post_stem_count[si]))

# 2-second 버킷 in 30-40s
print('\n  --- 2s 버킷별 filtered 노트 수 ---')
for b in range(int(T_START), int(T_END), 2):
    cnt = sum(1 for t, _, _ in filtered if b <= t < b + 2)
    print('  %4ds-%4ds: %2d %s' % (b, b + 2, cnt, '#' * cnt))

# stem 별 RMS in 30-40s (어느 stem 이 dominant 인지)
print('\n  --- 30-40s RMS per stem ---')
s_idx, e_idx = int(T_START * sr), int(T_END * sr)
for si in sorted(stems.keys()):
    chunk = stems[si][s_idx:e_idx]
    rms = float(np.sqrt(np.mean(chunk * chunk)))
    bar = '#' * min(60, int(rms * 300))
    print('  stem %d (%-7s) rms %.4f  %s' % (si, STEM_NAMES[si], rms, bar))
