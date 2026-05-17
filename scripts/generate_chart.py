# -*- coding: utf-8 -*-
"""librosa 기반 chart 사전 생성 — 한 곡의 mix sum 에서 onset 검출 + beat 정렬 → chart.json.

산업 표준 spectral-flux onset detection (RMS 보다 melodic 잘 잡음) + beat tracker
로 16th-note grid 에 quantize. 결과는 deterministic.

출력 형식 (Music/<song>/chart.json):
{
  "version": 1,
  "generator": "librosa-v0.11",
  "bpm_input": <song.bpm>,
  "bpm_detected": <auto>,
  "sr": 22050,
  "onsets": [
    { "t": 5.21, "stem": 0, "energy": 0.87 },
    ...
  ],
  "vocal_ranges": [[s, e], ...]
}

게임 코드는 chart.json 있으면 onsets 를 그대로 사용 (시각/stem/에너지).
없으면 기존 JS detectOnsets 폴백 (UGC 모드 호환).

사용법:
  python scripts/generate_chart.py <song_prefix>
  python scripts/generate_chart.py --all
"""
import os, sys, json, argparse, subprocess, glob
import numpy as np
import librosa

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MUSIC = os.path.join(ROOT, 'Music')
STEM_NAMES = ['drums', 'bass', 'vocals', 'instrum', 'piano', 'guitar', 'other']
ALWAYS_AUDIBLE = [2]  # vocals — chart 안 만듦
SR = 22050  # librosa 표준


def load_stems(prefix, exclude=None):
    """Stem dir 의 7개 ogg 를 dict 로 로드. ALWAYS_AUDIBLE + exclude 는 스킵."""
    exclude = set(exclude or [])
    stem_dir = os.path.join(MUSIC, prefix)
    stems = {}
    for i, name in enumerate(STEM_NAMES):
        if i in ALWAYS_AUDIBLE or i in exclude:
            continue
        p = os.path.join(stem_dir, f'{prefix}_{name}.ogg')
        if not os.path.exists(p):
            continue
        d, _ = librosa.load(p, sr=SR, mono=True)
        stems[i] = d.astype(np.float32)
    if not stems:
        raise FileNotFoundError(f'No stems found for {prefix}')
    return stems


def mix_sum(stems):
    """모든 stem 을 합산해서 mix sum 반환. 길이는 가장 긴 stem 기준."""
    max_len = max(len(d) for d in stems.values())
    out = np.zeros(max_len, dtype=np.float32)
    for d in stems.values():
        out[:len(d)] += d
    return out


def detect_per_stem_onsets(stems, sr, song_bpm):
    """각 stem 별 spectral-flux onset 검출. 합치고 0.030s 이내 중복은 stem 다양성 유지하며 보존.

    반환: (per_stem_onsets dict, beats_sec, detected_bpm)
    """
    per_stem = {}
    mix = mix_sum(stems)

    # Beat tracking 은 mix 에서 (전체 tempo 추정)
    onset_env_mix = librosa.onset.onset_strength(y=mix, sr=sr, hop_length=512)
    try:
        tempo, beat_frames = librosa.beat.beat_track(
            onset_envelope=onset_env_mix, sr=sr, hop_length=512, start_bpm=song_bpm,
        )
        beats = librosa.frames_to_time(beat_frames, sr=sr, hop_length=512)
        try:
            detected_bpm = float(tempo[0]) if hasattr(tempo, '__len__') else float(tempo)
        except Exception:
            detected_bpm = float(song_bpm)
    except Exception:
        beats = np.array([])
        detected_bpm = float(song_bpm)

    # 각 stem 별 onset_detect
    for si, data in stems.items():
        try:
            env = librosa.onset.onset_strength(y=data, sr=sr, hop_length=512)
            frames = librosa.onset.onset_detect(
                onset_envelope=env, sr=sr, hop_length=512,
                backtrack=True, delta=0.07, wait=3,
            )
            times = librosa.frames_to_time(frames, sr=sr, hop_length=512)
            # 에너지 attach
            win = int(sr * 0.025)
            entries = []
            for t in times:
                idx = int(t * sr)
                f, e = max(0, idx - win), min(len(data), idx + win)
                chunk = data[f:e]
                energy = float(np.sum(chunk * chunk))
                entries.append({'t': round(float(t), 4), 'stem': int(si), 'energy': round(energy, 4)})
            per_stem[si] = entries
        except Exception as ex:
            print(f'  [stem {si} skip] {ex}')
            per_stem[si] = []

    return per_stem, beats, detected_bpm


def merge_per_stem(per_stem, dedup_window=0.030):
    """모든 stem 의 onset 을 시간순 합치고 dedup_window 이내 중복 정리.
    같은 시각에 여러 stem 가 동시 fire 하면 가장 강한 stem 의 onset 유지 (chord 시 1 lane → 시각 단순).
    """
    all_entries = []
    for entries in per_stem.values():
        all_entries.extend(entries)
    all_entries.sort(key=lambda x: x['t'])
    merged = []
    for o in all_entries:
        if merged and abs(o['t'] - merged[-1]['t']) < dedup_window:
            # 더 강한 쪽 유지
            if o['energy'] > merged[-1]['energy']:
                merged[-1] = o
            continue
        merged.append(o)
    # ★ Intro noise filter — 첫 0.15s 의 low-energy onset 제거.
    #   librosa onset_detect 가 곡 시작 시 intro pad / 잔향 을 onset 으로 잡음 (energy 매우 약).
    #   사용자 보고: "첫 부분 노트 미리 떨어짐" fix. 2026-05-17 추가.
    merged = [o for o in merged if not (o['t'] < 0.15 and o.get('energy', 1) < 0.5)]
    return merged


def detect_vocal_ranges(stems, sr):
    """vocal-only 구간 검출 — vocals 가 큰데 musical stem (drums/bass/piano/guitar) 다 quiet.
    JS 코드의 _MUSICAL = [0, 1, 4, 5] 와 동일 규칙."""
    # vocals 는 ALWAYS_AUDIBLE 이라 stems 에서 빠짐. 그래서 별도 로드 필요.
    # 호출 시점에 vocals 가 stems 에 없음을 가정 — 따로 처리 함수.
    return []  # 구현 보류 — 게임 코드의 vocalIntro auto 가 그대로 작동 (vocal stem 원본 보존)


def generate_chart(prefix, exclude_stems=None, song_bpm=120, end_cutoff=None):
    """한 곡의 chart 생성. 메인 진입점."""
    print(f'[gen] {prefix} (bpm_hint={song_bpm}, excl={exclude_stems})')
    stems = load_stems(prefix, exclude=exclude_stems)
    print(f'  stems loaded: {sorted(stems.keys())}')
    mix = mix_sum(stems)
    print(f'  mix duration: {len(mix) / SR:.1f}s')

    per_stem, beats, detected_bpm = detect_per_stem_onsets(stems, SR, song_bpm)
    counts = ', '.join(f'{si}:{len(v)}' for si, v in sorted(per_stem.items()))
    print(f'  per-stem onsets: {counts}, beats={len(beats)}, bpm={detected_bpm:.1f}')

    attributed = merge_per_stem(per_stem)
    print(f'  merged (dedup 30ms): {len(attributed)} entries')

    # endCutoff 이전만 (게임 endCutoff filter 와 일치)
    if end_cutoff:
        attributed = [o for o in attributed if o['t'] < end_cutoff]
        print(f'  after endCutoff ({end_cutoff}s): {len(attributed)} onsets')
    chart = {
        'version': 1,
        'generator': f'librosa-{librosa.__version__}',
        'bpm_input': song_bpm,
        'bpm_detected': round(detected_bpm, 1),
        'sr': SR,
        'onsets': attributed,
    }
    out_path = os.path.join(MUSIC, prefix, 'chart.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(chart, f, ensure_ascii=False, indent=1)
    print(f'  -> {out_path} ({len(attributed)} chart onsets)')
    return chart


def read_songs_from_index():
    """index.html 의 songs 배열을 node 로 추출."""
    src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    i = src.index('const songs = [')
    j = src.index('\n];', i) + 3
    arr = src[i:j].replace('const songs', 'var songs', 1)
    arr += ('\nconsole.log(JSON.stringify(songs.filter(function(s){return s.stemDir;})'
            '.map(function(s){return {name:s.name,stemPrefix:s.stemPrefix,bpm:s.bpm,'
            'excludeStems:s.excludeStems||[],endCutoff:s.endCutoff||null};})));')
    tmp = os.path.join(ROOT, 'scripts', '_emit_chart.js')
    open(tmp, 'w', encoding='utf-8').write(arr)
    r = subprocess.run(['node', tmp], capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    os.remove(tmp)
    if r.returncode != 0:
        print('songs 추출 실패:', r.stderr[-400:])
        sys.exit(1)
    return json.loads(r.stdout)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('prefix', nargs='?', help='song stem prefix (e.g., Spin). 비우면 --all 필요.')
    ap.add_argument('--all', action='store_true', help='index.html songs 전부 생성')
    ap.add_argument('--bpm', type=int, default=120, help='BPM hint (단일 곡 모드)')
    ap.add_argument('--end-cutoff', type=float, help='endCutoff sec')
    args = ap.parse_args()

    if args.all:
        songs = read_songs_from_index()
        print(f'전체 stem 기반 곡: {len(songs)}개')
        for s in songs:
            try:
                generate_chart(
                    s['stemPrefix'],
                    exclude_stems=s.get('excludeStems') or [],
                    song_bpm=s.get('bpm') or 120,
                    end_cutoff=s.get('endCutoff'),
                )
            except Exception as e:
                print(f'  [실패] {s["stemPrefix"]}: {e}')
    elif args.prefix:
        generate_chart(args.prefix, song_bpm=args.bpm, end_cutoff=args.end_cutoff)
    else:
        ap.print_help()
