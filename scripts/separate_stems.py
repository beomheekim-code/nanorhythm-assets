# -*- coding: utf-8 -*-
"""
MP3 → 7 stem 분리 — Demucs htdemucs_6s + instrumental 합성.

add-song 스킬의 선행 단계. Music/<곡명>.mp3 를 감지해
Music/<곡명>/<곡명>_<stem>.ogg × 7 을 생성한다.
  - 메인 풀믹스 OGG (Music/<곡명>.ogg) 는 건드리지 않음 (add-song 이 MP3→OGG 담당).
  - 커버 PNG 도 건드리지 않음 (사용자가 따로 추가).
  - MP3 원본도 삭제하지 않음 (add-song 이 변환 후 삭제).

게임 stem 순서: drums, bass, vocals, instrum, piano, guitar, other
  - drums/bass/vocals/piano/guitar/other = demucs htdemucs_6s 직접 출력
  - instrum = drums+bass+piano+guitar+other 합 (MVSEP instrumental 재현, 검증 corr 0.997)

사용법:
  python scripts/separate_stems.py                  # Music/ 스캔, stem 폴더 없는 MP3 전부 처리
  python scripts/separate_stems.py <mp3경로>          # 해당 MP3 1개 처리
  python scripts/separate_stems.py <mp3경로> <출력폴더>  # 출력 폴더 지정 (테스트/대조용)
"""
import os, sys, subprocess, tempfile
import soundfile as sf
import numpy as np

ROOT = r'D:\nanorhythm-assets\nanorhythm-assets'
MUSIC = os.path.join(ROOT, 'Music')

# demucs htdemucs_6s 가 출력하는 stem
DEMUCS_STEMS = ['drums', 'bass', 'vocals', 'piano', 'guitar', 'other']
# 게임 index.html 의 stemNames 순서 — 이 순서/이름 그대로 파일 생성
GAME_STEMS = ['drums', 'bass', 'vocals', 'instrum', 'piano', 'guitar', 'other']

OGG_ARGS = ['-c:a', 'libopus', '-b:a', '128k', '-vbr', 'on', '-ar', '48000']


def separate_one(mp3_path, out_dir=None):
    """MP3 1개 → 7 stem OGG. 성공 시 True."""
    name = os.path.splitext(os.path.basename(mp3_path))[0]
    if out_dir is None:
        out_dir = os.path.join(MUSIC, name)
    os.makedirs(out_dir, exist_ok=True)
    print('[곡] %s' % name)

    with tempfile.TemporaryDirectory() as tmp:
        # 1) demucs htdemucs_6s — GPU, WAV 출력
        print('  demucs 분리 중 (GPU)...')
        cmd = [sys.executable, '-m', 'demucs', '-n', 'htdemucs_6s',
               '-d', 'cuda', '-o', tmp, mp3_path]
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        if r.returncode != 0:
            print('  [demucs 실패]\n' + (r.stderr or '')[-800:])
            return False

        sep_dir = os.path.join(tmp, 'htdemucs_6s', name)
        if not os.path.isdir(sep_dir):
            # demucs 가 트랙명을 다르게 잡는 경우 대비
            subdirs = [d for d in os.listdir(os.path.join(tmp, 'htdemucs_6s'))]
            if subdirs:
                sep_dir = os.path.join(tmp, 'htdemucs_6s', subdirs[0])

        # 2) 6 stem 로드
        data, sr = {}, None
        for s in DEMUCS_STEMS:
            wav = os.path.join(sep_dir, s + '.wav')
            if not os.path.exists(wav):
                print('  [실패] stem 누락: %s' % wav)
                return False
            x, sr = sf.read(wav)
            data[s] = x.astype(np.float32)

        # 2-b) 빈 stem 무음 게이트 — Demucs 는 악기가 없는 곡에도 미세 잔향(rms~0.003)을 남김.
        #   MVSEP 는 그런 stem 을 순수 무음(rms~0)으로 출력 → add-song 의 excludeStems
        #   자동판정(rms<0.001)이 작동. 게이트 없으면 잔향이 임계 위라 헛노트 유발.
        #   → 가장 큰 demucs stem 대비 5% 미만(또는 절대 0.005 미만)인 stem 은 무음 처리.
        rms = {s: float(np.sqrt(np.mean(data[s].astype(np.float64) ** 2))) for s in DEMUCS_STEMS}
        max_rms = max(rms.values()) if rms else 0.0
        gate = max(0.05 * max_rms, 0.005)
        for s in DEMUCS_STEMS:
            if rms[s] < gate:
                data[s] = np.zeros_like(data[s])
                print('  무음 게이트: %s (rms %.5f < %.5f)' % (s, rms[s], gate))

        # 3) instrum = 비-보컬 stem 합 (MVSEP instrumental 재현)
        #   정규화 안 함 — MVSEP 도 peak 1.05 정도 그대로 둠. 게임 gain staging
        #   (STEM_VOL * volBgm < 1.0) 이 >1.0 buffer 를 정상 처리. corr 0.996 확인.
        data['instrum'] = (data['drums'] + data['bass'] + data['piano']
                           + data['guitar'] + data['other'])
        _ip = float(np.abs(data['instrum']).max())
        if _ip > 1.5:  # 비정상 (분리 오류 의심) — 안전 정규화
            data['instrum'] = data['instrum'] / _ip
            print('  instrum peak=%.3f (>1.5 비정상) → 정규화' % _ip)

        # 4) WAV 임시 저장 → ffmpeg OGG 변환 → out_dir
        for s in GAME_STEMS:
            tmp_wav = os.path.join(tmp, '%s_final.wav' % s)
            sf.write(tmp_wav, data[s], sr)
            ogg = os.path.join(out_dir, '%s_%s.ogg' % (name, s))
            cr = subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', tmp_wav]
                                + OGG_ARGS + [ogg],
                                capture_output=True, text=True,
                                encoding='utf-8', errors='replace')
            if cr.returncode != 0 or not os.path.exists(ogg):
                print('  [ffmpeg 실패] %s\n%s' % (s, (cr.stderr or '')[-400:]))
                return False
            print('  생성: %s' % os.path.basename(ogg))

    print('  [완료] -> %s' % out_dir)
    return True


def scan_and_process():
    """Music/ 직하 MP3 중 stem 폴더가 없는 것 전부 처리."""
    if not os.path.isdir(MUSIC):
        print('[실패] Music 폴더 없음: %s' % MUSIC)
        return
    targets = []
    for f in sorted(os.listdir(MUSIC)):
        if not f.lower().endswith('.mp3'):
            continue
        name = f[:-4]
        stem_folder = os.path.join(MUSIC, name)
        # 이미 7 stem 다 있으면 skip
        if os.path.isdir(stem_folder):
            have = all(os.path.exists(os.path.join(stem_folder, '%s_%s.ogg' % (name, s)))
                       for s in GAME_STEMS)
            if have:
                print('[skip] %s — stem 이미 존재' % name)
                continue
        targets.append(os.path.join(MUSIC, f))
    if not targets:
        print('처리할 MP3 없음.')
        return
    print('처리 대상 %d곡: %s\n' % (len(targets), ', '.join(os.path.basename(t) for t in targets)))
    ok = 0
    for mp3 in targets:
        if separate_one(mp3):
            ok += 1
    print('\n=== %d/%d곡 stem 분리 완료 ===' % (ok, len(targets)))


if __name__ == '__main__':
    if len(sys.argv) == 1:
        scan_and_process()
    elif len(sys.argv) == 2:
        separate_one(sys.argv[1])
    else:
        separate_one(sys.argv[1], sys.argv[2])
