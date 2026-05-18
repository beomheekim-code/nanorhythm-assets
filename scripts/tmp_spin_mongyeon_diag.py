# -*- coding: utf-8 -*-
"""SPIN / 夢緣 mix-onset + drum-additive 시뮬레이션 — 갭/밀도 진단.

JS 의 detectOnsets + mix-onset + gap-fill + drum-add 파이프라인을 재현하여
실제 chart 시각이 어디에 떨어지는지 timestamp 출력.
"""
import os, sys, glob
import numpy as np, librosa
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
MUSIC = os.path.join(ROOT, 'Music')


def detect_onsets(data, sr, sens=1.05, min_gap_ms=30):
    """JS detectOnsets 동등 — RMS spike + smoothed baseline + min gap."""
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


def run_song(label, prefix, exclude_stems, end_cutoff):
    print('\n' + '=' * 70)
    print('곡: %s  (excludeStems=%s, endCutoff=%s)' % (label, exclude_stems, end_cutoff))
    print('=' * 70)
    stem_dir = os.path.join(MUSIC, prefix)
    stem_names = ['drums', 'bass', 'vocals', 'instrum', 'piano', 'guitar', 'other']
    stems = {}
    sr = None
    for i, sn in enumerate(stem_names):
        if i in exclude_stems:
            continue
        p = os.path.join(stem_dir, '%s_%s.ogg' % (prefix, sn))
        if not os.path.exists(p):
            print('  [없음] %s' % p)
            continue
        d, _sr = librosa.load(p, sr=22050, mono=True)
        stems[i] = d
        sr = _sr
    if sr is None:
        print('[로드 실패]')
        return

    # sum mix
    mxlen = max(len(d) for d in stems.values())
    sumbuf = np.zeros(mxlen, dtype=np.float64)
    for d in stems.values():
        sumbuf[:len(d)] += d
    mix_onsets = detect_onsets(sumbuf, sr, sens=1.05)
    tail_cut = end_cutoff - 1.0 if end_cutoff else 9999
    mix_onsets = [t for t in mix_onsets if t <= tail_cut]
    print('mix onsets: %d (tailCut=%.2f)' % (len(mix_onsets), tail_cut))

    # per-stem onsets (drum additive 후보)
    per_stem = {i: detect_onsets(stems[i], sr, sens=1.05) for i in stems}
    drum_onsets = per_stem.get(0, [])
    print('drum stem onsets: %d' % len(drum_onsets))

    # drum-add (mix-onset 과 0.08s 이내 중복 제외)
    DRUM_PROX = 0.08
    drum_added = []
    mix_sorted = sorted(mix_onsets)
    for dt in drum_onsets:
        if dt > tail_cut:
            continue
        near = False
        for mt in mix_sorted:
            if mt > dt + DRUM_PROX:
                break
            if abs(mt - dt) < DRUM_PROX:
                near = True
                break
        if not near:
            drum_added.append(dt)
    print('drum-add (mix 중복 제외): %d' % len(drum_added))

    # 전체 chart 시각
    all_times = sorted(set(mix_onsets) | set(drum_added))
    # gap 분석 (0.5s+ 갭)
    print('\n  --- 갭 (0.5s+) ---')
    big_gaps = []
    for i in range(len(all_times) - 1):
        gap = all_times[i + 1] - all_times[i]
        if gap >= 0.5:
            big_gaps.append((all_times[i], all_times[i + 1], gap))
    big_gaps.sort(key=lambda x: -x[2])
    for s, e, g in big_gaps[:15]:
        print('  %6.2fs ~ %6.2fs  gap %4.2fs' % (s, e, g))
    if not big_gaps:
        print('  (0.5s+ 갭 없음)')

    # 10s 버킷별 onset 수
    print('\n  --- 10s 버킷별 onset 수 ---')
    if all_times:
        max_t = max(all_times)
        for b in range(0, int(max_t) + 1, 10):
            cnt = sum(1 for t in all_times if b <= t < b + 10)
            bar = '#' * min(60, cnt)
            print('  %3d-%3d: %3d %s' % (b, b + 10, cnt, bar))

    # 마지막 10s RMS — 페이드/무음 구간 진단
    print('\n  --- 마지막 10s RMS (sum) ---')
    end_idx = min(int((end_cutoff or len(sumbuf) / sr) * sr), len(sumbuf))
    win = sr  # 1초 윈도우
    for sec in range(10, 0, -1):
        s_idx = end_idx - sec * sr
        e_idx = end_idx - (sec - 1) * sr
        if s_idx < 0:
            continue
        chunk = sumbuf[s_idx:e_idx]
        rms = float(np.sqrt(np.mean(chunk * chunk)))
        bar = '#' * min(40, int(rms * 200))
        print('  %5.1fs ~ %5.1fs (T-%2ds)  rms %.4f  %s' % (s_idx / sr, e_idx / sr, sec, rms, bar))

    # 마지막 5초 노트 밀도 (夢緣 용)
    if end_cutoff:
        last_5 = [t for t in all_times if end_cutoff - 5 < t <= end_cutoff]
        print('\n  마지막 5초 (%.1f ~ %.1f) 노트: %d개' % (end_cutoff - 5, end_cutoff, len(last_5)))
        last_2 = [t for t in all_times if end_cutoff - 2 < t <= end_cutoff]
        print('  마지막 2초 (%.1f ~ %.1f) 노트: %d개' % (end_cutoff - 2, end_cutoff, len(last_2)))


# SPIN: excludeStems=[4], endCutoff=138.7
run_song('Spin', 'Spin', [4], 138.7)

# 夢緣: excludeStems=[]  (이전 세션에서 빈 list 로 fix), endCutoff 확인 필요
mong_prefix = '夢緣_(몽연)'
# endCutoff 는 nullable. 일단 dur 로 처리 시도
mong_dir = os.path.join(MUSIC, mong_prefix)
if os.path.isdir(mong_dir):
    # 가장 긴 stem 길이로 dur 추정
    drum_p = os.path.join(mong_dir, '%s_drums.ogg' % mong_prefix)
    if os.path.exists(drum_p):
        d, sr = librosa.load(drum_p, sr=22050, mono=True)
        dur = len(d) / sr
        print('\n夢緣 dur ≈ %.1fs' % dur)
        run_song('夢緣', mong_prefix, [], dur)
    else:
        print('\n[夢緣 drum stem 없음]')
else:
    print('\n[夢緣 stem 폴더 없음 — prefix 확인 필요]')
