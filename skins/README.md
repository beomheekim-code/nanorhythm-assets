# 스킨 시스템 — 신규 스킨 추가 가이드

게임 내 전체 UI 자산(노트/홀드/키/판정텍스트/콤보/이펙트/HP바/레일/판정선)을 스킨 단위로 교체. 각 스킨은 `skins/{id}/` 하나의 폴더에 자립.

## 폴더 구조

```
skins/
  {id}/
    manifest.json           # 파일명·셀 크기·팔레트·매핑 정의
    note/                   # 노트 + 홀드 머리/꼬리/몸통 모두 여기서 파생
      01.png ~ 08.png       # 셀 소스 (숫자명, 빌드 스크립트 입력)
      {id}_note.png         # 노트 아틀라스 (rebuild 생성)
      {id}_holdbody.png     # 홀드 몸통 (generate_hold_body 생성)
    key/                    # 키 베이스 (업로드 대기)
    score_text/             # 점수 숫자 (업로드 대기)
    judgment_text/          # perfect/good/bad 텍스트 (대기)
    combo_text/             # 콤보 숫자 (대기)
    hit_effect/             # 히트 이펙트 (대기)
    hp_bar/                 # HP 바 (대기)
    lane/                   # 레일 (대기)
    judge_line/             # 판정선 (대기)
```

**규약**:
- **셀(소스)**: 숫자 파일명 `NN.png` (예: `01.png ~ 08.png`).
- **아틀라스(출력)**: `{skinId}_{category}.png` (예: `neon_note.png`, `neon_holdbody.png`) — glob 에서 숫자 패턴으로 셀과 자동 구분.
- 각 카테고리 폴더는 **자기 카테고리만** 담당. note 폴더에 key 넣지 말 것.

## manifest.json 스키마

```jsonc
{
  "id":   "neon",                // 고유 id (= 폴더명)
  "name": "벚꽃 네온",           // UI 표시 이름
  "files": {
    "note":     "note/neon_note.png",
    "holdHead": "note/neon_note.png",     // 머리 = 노트 공유
    "holdBody": "note/neon_holdbody.png"
    // 향후 "key": "key/neon_key.png", "scoreText": "score_text/neon_scoretext.png" 등
  },
  "cellsDir":       "note",                    // 셀이 들어있는 폴더 (카테고리와 동일)
  "cellSize":       400,
  "nCells":         8,
  "paletteCellMap": [0, 1, 7, 5, 3, 2, 6, 4],  // OLD 팔레트 idx → 소스 셀 idx
  "palette":        ["#b33f64","#d0afda","..."]
}
```

## 추가 워크플로

1. `skins/{id}/note/01.png ~ 08.png` 꽃 셀 8장 업로드 (정사각, 배경 어둡게 max<80).
2. `skins/{id}/manifest.json` 작성.
3. 빌드:
   ```bash
   python scripts/rebuild_note_from_cells.py {id}        # note atlas
   python scripts/generate_hold_body_from_notes.py {id}  # hold body atlas
   ```
4. `index.html` SKINS 에 항목 추가 (`imagePaths`/`sprites`/`palette`/`laneMapping`/`visualSize`).
5. 다른 카테고리(key, score_text, ...) 도 동일 패턴: 셀 업로드 → 빌드 스크립트 → SKINS 갱신.
6. 상점 UI 붙이면 `price`/`name` 자동 카탈로그화.

## 현재 스킨 목록

- `neon` — 벚꽃 네온 (첫 번째 스킨, 레퍼런스 구현, note 카테고리만 완성)
