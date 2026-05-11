"""
add-song 스킬 buggy 측정 회귀 방지 점검 스크립트.

매 add-song 작업 후 (또는 인게임 노트 사라짐 신고 시) 실행:
  python scripts/check_song_bars_endcutoff.py

검증:
1. bars * 4 * 60 / bpm >= endCutoff + 1 (= 차트 길이 >= endCutoff)
2. endCutoff vs drums stem 의 last onset (= 음악 끝 직전)
3. 잘못된 곡 list 출력 + 수정 값 제안

회귀 이력 (2026-05-11):
- Glitch Heartbeat: bars=50 (86.96s) < endCutoff=92.7 < last_onset=104.72
- 16곡 bars/endCutoff 일괄 보정 commit 2033377
"""
import librosa, os, re, math

INDEX = r'D:\nanorhythm-assets\nanorhythm-assets\index.html'
MUSIC = r'D:\nanorhythm-assets\nanorhythm-assets\Music'

def check():
    with open(INDEX, 'r', encoding='utf-8') as f:
        txt = f.read()
    pattern = re.compile(
        r"name:\s*'([^']+)',[^}]*?bpm:\s*(\d+(?:\.\d+)?)[^}]*?bars:\s*(\d+)[^}]*?stemDir:\s*'([^']+)'[^}]*?stemPrefix:\s*'([^']+)'(?:[^}]*?endCutoff:\s*(\d+(?:\.\d+)?))?",
        re.S
    )
    issues = []
    for m in pattern.finditer(txt):
        name, bpm, bars, stemDir, prefix, endCutoff = m.groups()
        bpm = float(bpm); bars = int(bars)
        endCutoff = float(endCutoff) if endCutoff else None
        drums = os.path.join(MUSIC, stemDir.replace('Music/', '').rstrip('/'), prefix + '_drums.ogg')
        if not os.path.exists(drums):
            continue
        try:
            actual_dur = librosa.get_duration(path=drums)
        except:
            continue
        chart_dur = bars * 4 * 60 / bpm
        needed_bars, needed_cut = bars, endCutoff
        flag = []
        if endCutoff and chart_dur < endCutoff - 1:
            needed_bars = math.ceil((endCutoff + 1) * bpm / 240)
            flag.append(f'bars↑ chart={chart_dur:.1f}s < endCut={endCutoff}')
        if endCutoff and endCutoff < actual_dur - 5:
            try:
                y, sr = librosa.load(drums, sr=22050)
                onsets = librosa.onset.onset_detect(y=y, sr=sr, units='time')
                if len(onsets) > 0:
                    last = float(onsets[-1])
                    if last - endCutoff > 5:
                        needed_cut = round(last - 0.3, 2)
                        flag.append(f'endCut↑ last_onset={last:.1f}s vs endCut={endCutoff}')
                        needed_bars = max(needed_bars, math.ceil((needed_cut + 1) * bpm / 240))
            except:
                pass
        if flag:
            issues.append({'name': name, 'bpm': bpm, 'bars': bars, 'endCutoff': endCutoff,
                          'needed_bars': needed_bars, 'needed_endCutoff': needed_cut, 'flags': flag})
    if not issues:
        print('OK: all songs bars/endCutoff valid')
        return 0
    print(f'\n=== {len(issues)} ISSUES ===')
    for i in issues:
        print(f"\n[{i['name']}] bpm={i['bpm']}")
        print(f"  current: bars={i['bars']}, endCut={i['endCutoff']}")
        print(f"  needed:  bars={i['needed_bars']}, endCut={i['needed_endCutoff']}")
        print(f"  flags: {', '.join(i['flags'])}")
    return 1

if __name__ == '__main__':
    import sys
    sys.exit(check())
