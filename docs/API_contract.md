# API Contract: React/Electron → AssetManager_UnityPy

## 실행 방식

Electron/React는 Python 내부 함수를 직접 호출하지 않는다.

항상 CLI 또는 exe를 호출한다.

```bash
AssetManager_UnityPy.exe --plan patch_plan.json --report patch_report.json
````

개발 중에는:

```bash
python -m asset_patcher.cli --plan patch_plan.json --report patch_report.json
```

---

# 공통 Plan 구조

```json
{
  "kind": "clothes",
  "dry_run": false,
  "stop_on_error": true
}
```

## 공통 필드

| 필드            | 타입      | 설명              |
|---------------|---------|-----------------|
| kind          | string  | 실행 종류           |
| dry_run       | boolean | 실제 저장 없이 검증만 수행 |
| stop_on_error | boolean | 에러 발생 시 즉시 중단   |

---

# kind 목록

```text
clothes       의상 PNG 패치
font_extract  원본 폰트 추출
font          폰트 교체
font_restore  원본 폰트 복원
```

---

# 1. Clothes Patch

## Plan

```json
{
  "kind": "clothes",
  "dry_run": false,
  "stop_on_error": true,
  "texture_metadata_path": "./metadata/data.tsv",
  "jobs": [
    {
      "request": {
        "game_id": "LongYinLiZhiZhuan",
        "category": "clothes",
        "option1": "female",
        "option2": "천산파",
        "texture_name": "skeleton_17",
        "pathID": 156,
        "size": [
          940,
          2061
        ]
      },
      "assets_file": "D:/Games/.../sharedassets1.assets",
      "png_file": "D:/Mods/.../skeleton_17.png",
      "flip_y": true
    }
  ]
}
```

## request 필드

| 필드           | 타입               | 설명               |
|--------------|------------------|------------------|
| game_id      | string           | 게임 ID            |
| category     | string           | clothes          |
| option1      | string           | gender           |
| option2      | string           | 의상 종류            |
| texture_name | string           | Texture2D 이름     |
| pathID       | number           | Texture2D PathID |
| size         | [number, number] | 원본 Texture2D 크기  |

## 중요

* atlas 파일 경로는 React에서 넘기지 않는다.
* atlas는 `data.tsv`의 `atlas_name`, `atlas_pathID` 기준으로 Python 쪽에서 처리한다.
* 동일 크기 PNG는 `.resS` 직접 patch.
* 크기 변경 PNG는 현재 비활성화.

---

# 2. Font Extract

```json
{
  "kind": "font_extract",
  "game_id": "LongYinLiZhiZhuan",
  "font_metadata_path": "./metadata/fonts_data.tsv",
  "originals_dir": "./originals",
  "assets_file": "D:/Games/.../resources.assets",
  "overwrite": false
}
```

---

# 3. Font Patch

```json
{
  "kind": "font",
  "game_id": "LongYinLiZhiZhuan",
  "dry_run": false,
  "stop_on_error": true,
  "font_metadata_path": "./metadata/fonts_data.tsv",
  "originals_dir": "./originals",
  "assets_file": "D:/Games/.../resources.assets",
  "jobs": [
    {
      "path_id": 2418,
      "replacement_font_file": "D:/Mods/fonts/MyFont.ttf"
    }
  ]
}
```

권장 기준은 `font_name`이 아니라 `path_id`다.

---

# 4. Font Restore

```json
{
  "kind": "font_restore",
  "game_id": "LongYinLiZhiZhuan",
  "dry_run": false,
  "stop_on_error": true,
  "font_metadata_path": "./metadata/fonts_data.tsv",
  "originals_dir": "./originals",
  "assets_file": "D:/Games/.../resources.assets",
  "jobs": [
    {
      "path_id": 2418
    }
  ]
}
```

---

# Report 구조

## 성공

```json
{
  "kind": "clothes",
  "status": "success",
  "dry_run": false,
  "stop_on_error": true,
  "success_count": 1,
  "failed_count": 0,
  "results": [],
  "errors": []
}
```

## 실패

```json
{
  "kind": "clothes",
  "status": "failed",
  "success_count": 0,
  "failed_count": 1,
  "results": [],
  "errors": [
    {
      "index": 0,
      "request": {},
      "error_type": "ValueError",
      "message": "..."
    }
  ]
}
```

---

# Electron 연동 원칙

## 권장 방식

```text
1. React에서 patch_plan.json 생성
2. Electron main process에서 child_process.spawn 실행
3. stdout/stderr 수집
4. patch_report.json 읽기
5. React에 결과 전달
```

## 직접 Python 모듈 import 금지

Electron에서 Python 내부 코드를 직접 호출하지 않는다.

이유:

* exe 빌드 후 구조 유지 쉬움
* 에러 처리 단순
* React와 Python 경계 명확
* 배포 안정성 높음

---

# 한글 경로 대응

Windows PowerShell/터미널에서는 한글 경로가 깨질 수 있다.

배포 시 권장 방식:

```text
1. Electron이 입력 파일을 work/input 폴더로 복사
2. patch_plan에는 work/input 기준 경로 기록
3. Python exe 실행
4. 결과 파일을 목적 위치로 복사
```

권장 작업 폴더:

```text
AssetManager_UnityPy/
├─ work/
│  ├─ input/
│  ├─ output/
│  └─ plans/
├─ reports/
├─ metadata/
└─ originals/
```

---

# Exit Code

| code | 의미 |
|------|----|
| 0    | 성공 |
| 1    | 실패 |

Electron은 exit code와 report JSON을 함께 확인해야 한다.
