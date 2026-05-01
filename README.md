# AssetManager_UnityPy

Unity 기반 게임의 Texture2D, Spine atlas, Font 리소스를 안전하게 교체하기 위한 Python 패치 도구입니다.

## 목표

- 의상 PNG 교체
- atlas txt 자동 보정
- resources.assets 내부 Font 교체
- React/Electron 앱에서 JSON plan을 전달해 실행
- 추후 Nuitka exe 빌드 지원

## 핵심 원칙

### Texture / PNG

- Texture2D 식별은 `PathID` 기준
- `texture_name`은 검증용
- 동일 크기 PNG는 `.resS` 직접 patch
- 크기가 다른 PNG는 UnityPy 최소 수정 patch
- atlas가 있는 경우 `size`, `bounds`, `offsets` 자동 배율 보정
- atlas 원본은 `.original` 파일로 최초 1회 보존

### Font

- `resources.assets` 내부 Font 객체 수정
- 대상은 `fonts_data.tsv`의 `PathID` 기준
- Arial도 TSV에 있으면 교체 대상
- 제외하려면 TSV에서 행 삭제
- 첫 실행 시 원본 Font data를 `originals/{game_id}/fonts`에 보관

## 현재 구조

```text
AssetManager_UnityPy/
├─ asset_patcher/
│  ├─ cli.py
│  ├─ models/
│  │  └─ patch_request.py
│  ├─ core/
│  │  ├─ atlas_manager.py
│  │  ├─ font_metadata.py
│  │  ├─ game_metadata.py
│  │  ├─ original_store.py
│  │  └─ texture_metadata.py
│  ├─ modules/
│  │  ├─ font_patch.py
│  │  ├─ texture_ress_patch.py
│  │  └─ texture_unitypy_patch.py
│  └─ services/
│     ├─ clothes_batch_service.py
│     └─ clothes_patch_service.py
├─ metadata/
│  ├─ data.tsv
│  └─ fonts_data.tsv
├─ examples/
│  ├─ clothes_patch.example.json
│  ├─ font_extract.example.json
│  ├─ font_patch.example.json
│  └─ font_restore.example.json
├─ originals/
├─ reports/
└─ README.md
````

## 설치

```bash
pip install UnityPy Pillow
```

## 실행 방식

```bash
python -m asset_patcher.cli --plan ./examples/clothes_patch.example.json --report ./reports/report.json
```

## Plan 종류

```text
kind=clothes       의상 PNG 패치
kind=font_extract  원본 폰트 추출
kind=font          폰트 교체
kind=font_restore  원본 폰트 복원
```

## Clothes patch plan

```json
{
  "kind": "clothes",
  "dry_run": true,
  "stop_on_error": true,
  "texture_metadata_path": "../metadata/data.tsv",
  "jobs": [
    {
      "request": {
        "game_id": "LongYinLiZhiZhuan",
        "category": "clothes",
        "option1": "female",
        "option2": "type_01",
        "texture_name": "skeleton_17",
        "pathID": 123456,
        "size": [1763, 1050]
      },
      "assets_file": "D:/Games/.../sharedassets1.assets",
      "png_file": "D:/Mods/.../skeleton_17.png",
      "atlas_file": "D:/Games/.../skeleton.atlas.txt",
      "output_assets_file": null,
      "flip_y": false
    }
  ]
}
```

## Font extract plan

```json
{
  "kind": "font_extract",
  "game_id": "LongYinLiZhiZhuan",
  "font_metadata_path": "../metadata/fonts_data.tsv",
  "originals_dir": "../originals",
  "assets_file": "D:/Games/.../resources.assets",
  "overwrite": false
}
```

## Font patch plan

```json
{
  "kind": "font",
  "game_id": "LongYinLiZhiZhuan",
  "dry_run": true,
  "stop_on_error": true,
  "font_metadata_path": "../metadata/fonts_data.tsv",
  "originals_dir": "../originals",
  "assets_file": "D:/Games/.../resources.assets",
  "output_file": null,
  "jobs": [
    {
      "path_id": 2418,
      "replacement_font_file": "D:/Mods/fonts/MyKoreanFont.ttf"
    }
  ]
}
```

## Font restore plan

```json
{
  "kind": "font_restore",
  "game_id": "LongYinLiZhiZhuan",
  "dry_run": true,
  "stop_on_error": true,
  "font_metadata_path": "../metadata/fonts_data.tsv",
  "originals_dir": "../originals",
  "assets_file": "D:/Games/.../resources.assets",
  "output_file": null,
  "jobs": [
    {
      "path_id": 2418
    }
  ]
}
```

## Texture patch 동작

### PNG 크기가 원본과 같을 때

```text
UnityPy로 Texture2D 정보 조회
→ PathID/name/size/format 검증
→ m_StreamData offset/size/path 확인
→ PNG를 RGBA32 raw bytes로 변환
→ .resS offset 위치에 직접 덮어쓰기
```

이 방식은 `.assets` 구조를 변경하지 않습니다.

### PNG 크기가 원본과 다를 때

```text
UnityPy로 Texture2D image data 교체
→ PathID/name/container snapshot 검증
→ atlas txt size/bounds/offsets 배율 수정
→ .assets 저장
```

이 방식은 실제 게임 테스트가 필요합니다.

## Atlas patch 동작

지원 atlas 형식:

```text
skeleton.png
size:2487,1081
filter:Linear,Linear
pma:true
scale:0.88
-100/右臂
bounds:1879,627,126,452
offsets:0,0,126,455
rotate:90
```

수정 대상:

```text
size    → page 크기
bounds  → x,y,w,h 전체 배율 수정
offsets → x,y,w,h 전체 배율 수정
```

수정하지 않는 대상:

```text
rotate
filter
pma
scale
```

## Metadata

### data.tsv

의상 Texture2D 기준 데이터입니다.

필수 컬럼:

```text
category
gender
type
texture_name
pathID
size
atlas_name
atlas_pathID
format
```

React 요청의 `category=clothes`는 TSV의 `category=Outfit`으로 매핑됩니다.

### fonts_data.tsv

Font 기준 데이터입니다.

필수 컬럼:

```text
Name
Description
Type
PathID
Source
```

Font 이름이 중복될 수 있으므로 실사용에서는 `path_id` 기준 patch를 권장합니다.

## 안전장치

* PathID 기준 검증
* Texture name 검증
* Texture size 검증
* RGBA32 format 검증
* `.resS` stream size 검증
* UnityPy 저장 전후 container snapshot 검증
* atlas 원본 `.original` 최초 1회 보존
* font 원본 data 최초 1회 보존
* `dry_run` 지원

## 권장 테스트 순서

### 1. Font 원본 추출

```bash
python -m asset_patcher.cli --plan ./examples/font_extract.example.json
```

### 2. 의상 dry run

```bash
python -m asset_patcher.cli --plan ./examples/clothes_patch.example.json
```

### 3. 동일 크기 PNG 1개 실제 patch

```json
"dry_run": false
```

### 4. 게임 실행 테스트

### 5. 크기 변경 PNG patch 테스트

### 6. Font patch 테스트

## 주의사항

* 동일 크기 PNG는 `.resS` 직접 patch가 우선입니다.
* 크기 변경 PNG는 UnityPy 저장이 필요하므로 반드시 테스트해야 합니다.
* Font patch는 `resources.assets`를 수정하므로 원본 font 추출 후 진행해야 합니다.
* 여러 atlas page를 한 번에 바꿀 때는 batch plan을 사용해야 atlas 변경이 누적됩니다.


---
해당 README.md 파일은 llm을 통해 작성했습니다.

