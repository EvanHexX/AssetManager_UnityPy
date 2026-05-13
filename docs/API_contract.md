# API Contract: AssetManager_UnityPy

React/Electron 쪽에서는 Python 함수를 직접 import하지 않고 CLI 또는 빌드된 exe를 실행한다.

```bash
AssetManager_UnityPy.exe --plan patch_plan.json --report patch_report.json
```

개발 중에는 다음 명령을 사용한다.

```bash
python -m asset_patcher.cli --plan patch_plan.json --report patch_report.json
```

## Common Plan

모든 plan은 JSON 객체이며 `kind`로 실행할 작업을 선택한다. 상대 경로는 plan 파일이 있는 폴더를 기준으로 해석된다.

```json
{
  "kind": "clothes",
  "dry_run": false,
  "stop_on_error": true
}
```

| Field           | Type    | Description     |
|-----------------|---------|-----------------|
| `kind`          | string  | 실행 종류           |
| `dry_run`       | boolean | 실제 저장 없이 검증만 수행 |
| `stop_on_error` | boolean | 오류 발생 시 즉시 중단   |

## Kind List

```text
clothes       의상 Texture2D/atlas 패치
font_list     현재 resources.assets의 Font PathID와 추출 파일명 조회
font_extract  원본 Font data 추출
font          Font data 교체
font_restore  원본 Font data 복원
ui_texture    UI Texture2D DXT5 .resS 직접 교체
```

## 1. Clothes Patch

```json
{
  "kind": "outfit",
  "dry_run": false,
  "stop_on_error": true,
  "texture_metadata_path": "../metadata/data.tsv",
  "originals_dir": "../originals",
  "jobs": [
    {
      "request": {
        "game_id": "LongYinLiZhiZhuan",
        "category": "clothes",
        "option1": "female",
        "option2": "type_01",
        "texture_name": "skeleton_17",
        "pathID": 156,
        "size": [
          940,
          2061
        ]
      },
      "assets_file": "D:/Games/.../sharedassets1.assets",
      "png_file": "D:/Mods/.../skeleton_17.png",
      "atlas_file": null,
      "output_assets_file": null,
      "flip_y": true
    }
  ]
}
```

## 2. Font List

현재 `resources.assets` 안의 `Font` 객체를 읽고, 각 폰트의 PathID와 원본 추출 시 사용되는 파일명만 출력한다. 파일을 저장하거나 수정하지 않는다.

### Plan

```json
{
  "kind": "font_list",
  "font_display_metadata_path": "./metadata/font_display_info.json",
  "assets_file": "D:/Games/.../resources.assets"
}
```

### Output

```json
{
  "kind": "font_list",
  "status": "success",
  "assets_file": "D:/Games/.../resources.assets",
  "count": 2,
  "fonts": [
    {
      "path_id": 2418,
      "font_file_name": "2418_SourceHanSerifCN-Medium.fontdata"
    },
    {
      "path_id": 2423,
      "font_file_name": "2423_Roboto-Bold.fontdata"
    }
  ]
}
```

`font_file_name`은 `font_extract`가 `originals/{game_id}/fonts` 아래에 저장할 때 쓰는 파일명 규칙과 같다.

`font_display_metadata_path`는 선택 필드다. 지정하면 `font_list` 결과를 표시용 JSON에 동기화한다. 표시용 JSON에는 `2418_SourceHanSerifCN-Medium.fontdata` 대신 `SourceHanSerifCN-Medium.otf`처럼 미리보기 가능한 폰트 파일명을 저장한다.

## 3. Font Extract

`fonts_data.tsv`에 등록된 Font의 원본 data를 `originals/{game_id}/fonts` 아래에 저장한다.

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

## 4. Font Patch

권장 기준은 `font_name`이 아니라 `path_id`다.

```json
{
  "kind": "font",
  "game_id": "LongYinLiZhiZhuan",
  "dry_run": false,
  "stop_on_error": true,
  "font_metadata_path": "./metadata/fonts_data.tsv",
  "font_display_metadata_path": "./metadata/font_display_info.json",
  "originals_dir": "./originals",
  "assets_file": "D:/Games/.../resources.assets",
  "output_file": null,
  "jobs": [
    {
      "path_id": 2418,
      "replacement_font_file": "D:/Mods/fonts/MyFont.ttf"
    }
  ]
}
```

패치가 성공하고 `dry_run`이 `false`이면 `font_display_metadata_path`의 같은 `path_id` 항목을 `replacement_font_file`의 파일명으로 갱신한다.

## Font Display Metadata

기본 파일은 `metadata/font_display_info.json`이다.

```json
{
  "game_id": "LongYinLiZhiZhuan",
  "preview_font_dir": "resources/tools/AssetManager/originals/LongYinLiZhiZhuan/fonts",
  "fonts": [
    {
      "path_id": 2418,
      "font_file_name": "SourceHanSerifCN-Medium.otf"
    }
  ]
}
```

## 5. Font Restore

```json
{
  "kind": "font_restore",
  "game_id": "LongYinLiZhiZhuan",
  "dry_run": false,
  "stop_on_error": true,
  "font_metadata_path": "./metadata/fonts_data.tsv",
  "originals_dir": "./originals",
  "assets_file": "D:/Games/.../resources.assets",
  "output_file": null,
  "jobs": [
    {
      "path_id": 2418
    }
  ]
}
```

## 6. UI Texture Patch

UI Texture2D는 `.assets`를 UnityPy로 검증하되 저장하지 않고, 기존 `m_StreamData`가 가리키는 `.resS` bytes만 교체한다.

```json
{
  "kind": "ui_texture",
  "game_id": "LongYinLiZhiZhuan",
  "data_dir": "D:/Games/.../LongYinLiZhiZhuan_Data",
  "dry_run": true,
  "stop_on_error": true,
  "ui_texture_metadata_path": "./metadata/ui_textures.tsv",
  "originals_dir": "./originals",
  "jobs": [
    {
      "path_id": 611,
      "png_file": "D:/Mods/ui/611_title_ui.png"
    }
  ]
}
```

제약:

- 현재 지원 format은 `DXT5`다.
- PNG 크기는 TSV의 `width`, `height`와 같아야 한다.
- DXT5 encoded byte size가 기존 `m_StreamData.size`와 같을 때만 저장한다.

## Report

### Success

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

### Error

```json
{
  "status": "error",
  "error_type": "ValueError",
  "message": "..."
}
```

### Failed Batch

```json
{
  "kind": "font",
  "status": "failed",
  "success_count": 0,
  "failed_count": 1,
  "results": [],
  "errors": [
    {
      "index": 0,
      "job": {},
      "error_type": "ValueError",
      "message": "..."
    }
  ]
}
```

## Exit Code

| Code | Meaning |
|------|---------|
| `0`  | 성공      |
| `1`  | 실패      |

Electron은 exit code와 report JSON을 함께 확인한다.

## Backup Path Rules

Texture 원본 raw:

```text
originals/{game_id}/textures/{pathID}_{texture_name}.rgba
```

Atlas 원본 txt:

```text
originals/{game_id}/atlas/{atlas_pathID}_{atlas_name}.txt
```

Font 원본 data:

```text
originals/{game_id}/fonts/{pathID}_{font_name}.fontdata
```

예:

```text
originals/LongYinLiZhiZhuan/fonts/2418_SourceHanSerifCN-Medium.fontdata
```
