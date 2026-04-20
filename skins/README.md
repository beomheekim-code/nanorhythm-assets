# 스킨 시스템 — 신규 스킨 추가 가이드

게임 내 노트/홀드/키 디자인을 스킨 단위로 교체 가능. 각 스킨은 `skins/{id}/` 하나의 폴더에 자립.

## 폴더 구조

```
skins/
  {id}/
    manifest.json              # 파일명·셀 크기·팔레트·매핑 정의
    note/
      _cells/note/*.png        # 셀별 꽃 소스 (8 장, rebuild 스크립트 입력)
      {NOTE}.png               # 노트 아틀라스 (rebuild 생성)
      {HOLD_BODY}.png          # 홀드 몸통 (generate_hold_body 생성)
      {KEY}.png                # 키 베이스 (수동 제작)
      {KEY_OVERLAY}.png        # 키 위 꽃 오버레이 (수동 제작)
```

## manifest.json 스키마

```jsonc
{
  "id":   "neon",                // 고유 id (= 폴더명)
  "name": "벚꽃 네온",           // UI 표시 이름
  "files": {
    "note":       "note/벚꽃_노트.png",
    "holdHead":   "note/벚꽃_노트.png",     // 머리 = 노트 공유
    "holdBody":   "note/벚꽃_홀드몸통.png",
    "key":        "note/벚꽃_노트키.png",
    "keyOverlay": "note/벚꽃_노트키_오버레이.png"
    // "holdHeadSilhouette": "..."         // 선택: 단색 silhouette 사용하는 스킨만
  },
  "cellsDir":       "note/_cells/note",
  "cellSize":       400,
  "nCells":         8,
  "paletteCellMap": [0, 1, 7, 5, 3, 2, 6, 4],   // OLD 팔레트 idx → 소스 셀 idx
  "palette":        ["#b33f64","#d0afda","..."] // 글로우/폴백용 hex 8 색
}
```

## 추가 워크플로

1. `skins/{id}/note/_cells/note/01.png ~ 08.png` 에 꽃 셀 8 장 배치 (정사각, 배경은 max<80 어두운 색).
2. `skins/{id}/manifest.json` 작성 (위 스키마).
3. 스크립트 실행 (skin id 파라미터로):
   ```bash
   python scripts/rebuild_note_from_cells.py {id}         # → 노트 PNG 생성
   python scripts/generate_hold_body_from_notes.py {id}   # → 홀드 몸통 PNG 생성
   ```
4. `index.html` 의 `SKINS` 객체에 항목 추가 (`imagePaths`/`sprites`/`palette`/`laneMapping`/`visualSize` 등).
5. 상점 UI 붙이면 `price`/`name` 자동 카탈로그화 예정.

## 현재 스킨 목록

- `neon` — 벚꽃 네온 (첫 번째 스킨, 레퍼런스 구현)
