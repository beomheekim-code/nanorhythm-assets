# -*- coding: utf-8 -*-
"""UGC code revert + 깔끔 재구현. 모든 UGC 흔적 제거 후 minimal block 1개로 재작성."""
import re, sys, shutil
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

PATH = r'D:\nanorhythm-assets\nanorhythm-assets\index.html'
shutil.copy(PATH, PATH + '.before_ugc_revert.bak')
print('backup OK')

with open(PATH, encoding='utf-8') as f:
    content = f.read()

# === 1. 4 mode 레이아웃 → 3 mode 복원 ===
content = content.replace(
    '''    // 세 모드 버튼
    // 모드 4개 — 4번째 = 나만의 모드 (28일 패스 필요, 2026-05-17)
    const _modeCount = 4;
    const pmBtnW = Math.min(sz(105), W*0.225), pmBtnH = sz(56), pmGap = sz(8);
    const pmTotalW = pmBtnW * _modeCount + pmGap * (_modeCount - 1);
    const pmStartX = (W - pmTotalW) / 2, pmY = _visY(0.58);
    loginModeBtnAreas = [];
    const modes = [
      { key: 'normal', label: '클래식', desc: '기본적인 플레이 모드입니다', color: '#00d4ff' },
      { key: 'freestyle', label: '프리스타일', desc: 'HP 압박없이 곡을 온전히 연주 하실 수 있습니다', color: '#ffd700' },
      { key: 'mymusic', label: '나만의 모드', desc: '내 음악 파일로 직접 차트 생성 (28일 패스 필요)', color: '#b464ff' },
      { key: 'versus', label: '온라인', desc: '준비 중입니다', color: '#ff6b6b' },
    ];''',
    '''    // 세 모드 버튼
    const pmBtnW = Math.min(sz(120), W*0.30), pmBtnH = sz(56), pmGap = sz(10);
    const pmTotalW = pmBtnW * 3 + pmGap * 2;
    const pmStartX = (W - pmTotalW) / 2, pmY = _visY(0.58);
    loginModeBtnAreas = [];
    const modes = [
      { key: 'normal', label: '클래식', desc: '기본적인 플레이 모드입니다', color: '#00d4ff' },
      { key: 'freestyle', label: '프리스타일', desc: 'HP 압박없이 곡을 온전히 연주 하실 수 있습니다', color: '#ffd700' },
      { key: 'mymusic', label: '나만의 모드', desc: '내 음악 파일로 직접 차트 생성 (28일 패스 필요)', color: '#b464ff' },
      { key: 'versus', label: '온라인', desc: '준비 중입니다', color: '#ff6b6b' },
    ];'''
)
print('mode 레이아웃 복원 (3 modes layout + 4번째 mymusic 옵션 유지)')

# === 2. title click handler — _ugcOverlayEl 가드 제거 (2 위치) ===
content = content.replace(
    '''  if (state === 'title') {
    if (!_preloadDone) return;
    if (_ugcOverlayEl) return; // UGC overlay 떠 있으면 캔버스 클릭 차단
    const mx = e.clientX, my = gameY(e.clientY);''',
    '''  if (state === 'title') {
    if (!_preloadDone) return;
    const mx = e.clientX, my = gameY(e.clientY);'''
)
content = content.replace(
    '''  if (state === 'title') {
    if (!_preloadDone) return;
    if (_ugcOverlayEl) return; // UGC overlay 떠 있으면 캔버스 터치 차단
    const t = e.changedTouches[0];''',
    '''  if (state === 'title') {
    if (!_preloadDone) return;
    const t = e.changedTouches[0];'''
)
print('title click 가드 제거 (2 위치)')

# === 3. 모드 click handler — mymusic 28일 패스 게이트는 유지 (좋은 패턴) ===
# (변경 없음)

# === 4. title confirm — mymusic 분기 유지 (clean rewrite 에서 사용) ===
# (변경 없음)

# === 5. UGC 함수 블록 통째 제거 + 클린 재작성으로 교체 ===
ugc_block_old = '''
// ===== 나만의 모드 (UGC) — Stage 1+2 (2026-05-17) =====
// 유저가 MP3 업로드 → 브라우저에서 decode → onset 검출 → 차트 생성 → 'select' 진입.
// 28일 패스 (hasActivePass) 구매자만 사용 가능 (gate 는 title 클릭 핸들러).
let _ugcInput = null;
let _ugcSong = null; // 현재 UGC 곡 (songs 배열에 임시 push 됨)
let _ugcProcessing = false;'''

assert ugc_block_old in content, 'UGC 변수 블록 못 찾음'

# 함수 정의 블록 통째로 찾기 — `// ===== 나만의 모드 (UGC) =====` 부터 `function audioBuffer...` 직전까지
m = re.search(
    r'// ===== 나만의 모드 \(UGC\).*?(?=// ===== 허공 입력)',
    content, re.DOTALL
)
assert m, 'UGC 함수 블록 영역 못 찾음'
print(f'UGC 블록 size: {len(m.group(0))} chars')

ugc_clean = '''// ===== 나만의 모드 (UGC, 2026-05-17 깔끔 재구현) =====
// MP3/OGG 업로드 → decode → onset 차트 → 인게임 1회성 플레이 → 타이틀 복귀.
// 28일 패스 (hasActivePass) 구매자만. songs[] 에 임시 push, cleanup 보장.
let _ugcInput = null;
let _ugcSong = null;
let _ugcProcessing = false;
let _ugcOverlayEl = null;

function showMyMusicFilePicker() {
  if (_ugcProcessing) return;
  if (!_ugcInput) {
    _ugcInput = document.createElement('input');
    _ugcInput.type = 'file';
    _ugcInput.accept = '.mp3,.ogg,audio/mpeg,audio/ogg';
    _ugcInput.style.cssText = 'position:fixed;left:-9999px;top:-9999px;';
    document.body.appendChild(_ugcInput);
    _ugcInput.addEventListener('change', handleMyMusicFile);
  }
  _ugcInput.value = '';
  _ugcInput.click();
}

async function handleMyMusicFile(e) {
  const f = e.target.files && e.target.files[0];
  if (!f) return;
  const lower = (f.name || '').toLowerCase();
  if (!lower.endsWith('.mp3') && !lower.endsWith('.ogg') &&
      f.type !== 'audio/mpeg' && f.type !== 'audio/ogg') {
    showLoginToast('MP3 또는 OGG 만 가능', '#ff6b6b', null, 2);
    return;
  }
  _ugcProcessing = true;
  try {
    showLoginToast(lower.endsWith('.ogg') ? '디코드 중...' : '변환 중...', '#b464ff', null, 60);
    resumeAudio();
    const arrayBuf = await f.arrayBuffer();
    const audioBuf = await actx.decodeAudioData(arrayBuf.slice(0));
    const onsetsRaw = detectOnsets(audioBuf, 1.10, 30);
    const STEMS = [0, 1, 3, 5, 6]; // drums/bass/instrum/guitar/other 라운드로빈
    const chartOnsets = onsetsRaw.map((t, i) => ({ t: +t.toFixed(4), stem: STEMS[i % STEMS.length], energy: 1 }));
    const blobUrl = URL.createObjectURL(f);
    const baseName = (f.name.replace(/\\.[^.]+$/, '') || '나만의 곡').slice(0, 28);
    const dur = audioBuf.duration;
    _ugcSong = {
      name: baseName, sub: 'MY MUSIC', bpm: 120,
      color: '#b464ff', bg1: '#0a0418', bg2: '#1a0830',
      bars: Math.ceil(dur / 2),
      file: blobUrl, cover: '',
      pattern: [1,0,0,0, 0,0,0,0, 1,0,0,0, 0,0,0,0],
      _ugc: true,
      _audioBuffer: audioBuf,
      _chartJson: { version: 1, generator: 'js-ugc', bpm_input: 120, bpm_detected: 120, sr: audioBuf.sampleRate, onsets: chartOnsets },
    };
    showUgcSetupOverlay();
  } catch (err) {
    console.error('[ugc] error', err);
    showLoginToast('파일 처리 실패: ' + (err && err.message || err), '#ff6b6b', null, 3);
  } finally {
    _ugcProcessing = false;
  }
}

function showUgcSetupOverlay() {
  if (_ugcOverlayEl) { _ugcOverlayEl.remove(); _ugcOverlayEl = null; }
  const el = document.createElement('div');
  el.style.cssText = 'position:fixed;left:0;top:0;width:100%;height:100%;background:rgba(0,0,0,0.78);z-index:9999;display:flex;align-items:center;justify-content:center;color:#fff;font-family:sans-serif;padding:20px;box-sizing:border-box;';
  el.innerHTML = '<div style="background:linear-gradient(135deg,#1a0830,#0a0418);padding:24px 28px;border-radius:14px;border:1px solid #b464ff66;max-width:380px;width:100%;">' +
    '<div style="font-size:18px;font-weight:bold;color:#b464ff;margin-bottom:6px;">나만의 모드</div>' +
    '<div style="font-size:13px;color:#ccc;margin-bottom:18px;word-break:break-all;">' + ((_ugcSong && _ugcSong.name) || '곡') + '</div>' +
    '<div style="font-size:11px;color:#aaa;margin-bottom:6px;">난이도</div>' +
    '<div id="ugcDiff" style="display:flex;gap:6px;margin-bottom:14px;">' +
      ['쉬움','보통','어려움','지옥'].map(function(n,i){return '<button data-i="'+i+'" style="flex:1;padding:9px 0;background:rgba(255,255,255,0.06);border:1px solid #b464ff44;color:#fff;border-radius:8px;cursor:pointer;font-size:12px;">'+n+'</button>';}).join('') +
    '</div>' +
    '<div style="font-size:11px;color:#aaa;margin-bottom:6px;">배속</div>' +
    '<div style="display:flex;gap:6px;margin-bottom:14px;align-items:center;">' +
      '<button id="ugcSpdMinus" style="padding:9px 14px;background:rgba(255,255,255,0.06);border:1px solid #b464ff44;color:#fff;border-radius:8px;cursor:pointer;font-size:16px;font-weight:bold;">−</button>' +
      '<div id="ugcSpdValue" style="flex:1;text-align:center;padding:9px 0;background:rgba(255,255,255,0.04);border:1px solid #b464ff44;border-radius:8px;font-size:14px;font-weight:bold;color:#b464ff;">1.0x</div>' +
      '<button id="ugcSpdPlus" style="padding:9px 14px;background:rgba(255,255,255,0.06);border:1px solid #b464ff44;color:#fff;border-radius:8px;cursor:pointer;font-size:16px;font-weight:bold;">+</button>' +
    '</div>' +
    '<div style="font-size:11px;color:#aaa;margin-bottom:6px;">키 수</div>' +
    '<div id="ugcKeys" style="display:flex;gap:6px;margin-bottom:18px;">' +
      [4,5,6,7,8].map(function(k){return '<button data-k="'+k+'" style="flex:1;padding:9px 0;background:rgba(255,255,255,0.06);border:1px solid #b464ff44;color:#fff;border-radius:8px;cursor:pointer;font-size:12px;">'+k+'K</button>';}).join('') +
    '</div>' +
    '<div style="display:flex;gap:8px;">' +
      '<button id="ugcCancel" style="flex:1;padding:11px 0;background:rgba(255,255,255,0.06);border:1px solid #888;color:#ccc;border-radius:8px;cursor:pointer;font-size:13px;">취소</button>' +
      '<button id="ugcStart" style="flex:2;padding:11px 0;background:#b464ff;border:0;color:#fff;border-radius:8px;cursor:pointer;font-size:13px;font-weight:bold;">시작</button>' +
    '</div>' +
  '</div>';
  document.body.appendChild(el);
  _ugcOverlayEl = el;
  let pickDiff = 1, pickSpeed = 1.0, pickKeys = 4;
  const markSel = (rootId, attr, val) => {
    el.querySelectorAll('#' + rootId + ' button').forEach(b => {
      const sel = String(b.getAttribute(attr)) === String(val);
      b.style.background = sel ? '#b464ff44' : 'rgba(255,255,255,0.06)';
      b.style.borderColor = sel ? '#b464ff' : '#b464ff44';
    });
  };
  const updSpd = () => { el.querySelector('#ugcSpdValue').textContent = pickSpeed.toFixed(1) + 'x'; };
  markSel('ugcDiff', 'data-i', pickDiff);
  markSel('ugcKeys', 'data-k', pickKeys);
  updSpd();
  el.querySelectorAll('#ugcDiff button').forEach(b => b.onclick = () => { pickDiff = +b.dataset.i; markSel('ugcDiff','data-i',pickDiff); });
  el.querySelectorAll('#ugcKeys button').forEach(b => b.onclick = () => { pickKeys = +b.dataset.k; markSel('ugcKeys','data-k',pickKeys); });
  el.querySelector('#ugcSpdMinus').onclick = () => { pickSpeed = Math.max(SPEED_MIN, +(pickSpeed - SPEED_STEP).toFixed(1)); updSpd(); };
  el.querySelector('#ugcSpdPlus').onclick = () => { pickSpeed = Math.min(SPEED_MAX, +(pickSpeed + SPEED_STEP).toFixed(1)); updSpd(); };
  el.querySelector('#ugcCancel').onclick = closeUgcOverlay;
  el.querySelector('#ugcStart').onclick = () => {
    selectedDiff = pickDiff;
    selectedSpeed = pickSpeed;
    laneCount = pickKeys;
    closeUgcOverlayKeep(); // overlay 만 닫고 _ugcSong 유지
    startUgcPlay();
  };
}

function closeUgcOverlay() {
  if (_ugcOverlayEl) { _ugcOverlayEl.remove(); _ugcOverlayEl = null; }
  _ugcSong = null;
}
function closeUgcOverlayKeep() {
  if (_ugcOverlayEl) { _ugcOverlayEl.remove(); _ugcOverlayEl = null; }
}

function startUgcPlay() {
  if (!_ugcSong) return;
  // 잔존 UGC entry 먼저 제거 (재진입 누적 방지)
  for (let i = songs.length - 1; i >= 0; i--) { if (songs[i] && songs[i]._ugc) songs.splice(i, 1); }
  songs.push(_ugcSong);
  selectedSong = songs.length - 1;
  startSong(selectedSong);
  transitionTo('playing');
}

// UGC cleanup — 플레이 끝나거나 취소 시 songs[] 에서 제거 + selectedSong 안전화.
function cleanupUgc() {
  let removed = false;
  for (let i = songs.length - 1; i >= 0; i--) {
    if (songs[i] && songs[i]._ugc) {
      try {
        if (songs[i].file && songs[i].file.startsWith('blob:')) URL.revokeObjectURL(songs[i].file);
      } catch(e) {}
      songs.splice(i, 1);
      removed = true;
    }
  }
  _ugcSong = null;
  if (_ugcOverlayEl) { try { _ugcOverlayEl.remove(); } catch(e) {} _ugcOverlayEl = null; }
  // selectedSong 가 UGC 마지막 인덱스였으면 splice 후 out-of-bounds → 0 으로
  if (removed && (selectedSong < 0 || selectedSong >= songs.length)) selectedSong = 0;
}

'''

content = content[:m.start()] + ugc_clean + content[m.end():]
print('UGC 함수 블록 깔끔 재작성')

# === 6. (다른 위치 변경 없음 — 기존 hooks 그대로 유지) ===
with open(PATH, 'w', encoding='utf-8') as f:
    f.write(content)
print('SKILL.md 형식 파일 저장 완료')
print('size diff (approx):', len(content), 'chars')
