# AssetManager_UnityPy

Unity 기반 게임의 Texture2D, Spine atlas, Font 리소스를 안전하게 교체하기 위한 Python 패치 도구입니다.

## 주요 기능

- 의상 Texture2D PNG 교체
- Spine atlas txt 자동 보정
- `resources.assets` 내부 Font data 조회, 추출, 교체, 복원
- 현재 표시용 Font 기본정보 JSON 관리
- React/Electron에서 JSON plan을 생성하고 CLI 또는 exe를 실행하는 구조
- `dry_run`과 원본 보존을 통한 안전한 패치 흐름

## 설치

```bash
pip install -r requirements.txt
```

## 실행

```bash
python -m asset_patcher.cli --plan ./examples/clothes_patch.example.json --report ./reports/report.json
```

빌드된 exe도 같은 계약을 사용합니다.

```bash
AssetManager_UnityPy.exe --plan patch_plan.json --report patch_report.json
```

## Plan 종류

```text
kind=clothes       의상 Texture2D/atlas 패치
kind=font_list     현재 Font PathID와 추출 파일명 조회
kind=font_extract  원본 Font data 추출
kind=font          Font data 교체
kind=font_restore  원본 Font data 복원
kind=ui_texture    UI Texture2D DXT5 .resS 직접 교체
```

## Font List Plan

현재 `resources.assets` 안의 Font 객체를 읽고 PathID와 추출 파일명만 출력합니다. 파일은 수정하지 않습니다.

```json
{
  "kind": "font_list",
  "font_display_metadata_path": "../metadata/font_display_info.json",
  "assets_file": "D:/Games/.../resources.assets"
}
```

출력 형식:

```json
{
  "kind": "font_list",
  "status": "success",
  "assets_file": "D:/Games/.../resources.assets",
  "count": 1,
  "fonts": [
    {
      "path_id": 2418,
      "font_file_name": "2418_SourceHanSerifCN-Medium.fontdata"
    }
  ]
}
```

`font_display_metadata_path`를 지정하면 조회 결과를 기준으로 표시용 JSON도 동기화합니다. 예를 들어 `2418_SourceHanSerifCN-Medium.fontdata`는 `SourceHanSerifCN-Medium.otf`로 저장됩니다.

## Font Extract Plan

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

## Font Patch Plan

실사용에서는 Font 이름보다 `path_id` 기준 패치를 권장합니다.

```json
{
  "kind": "font",
  "game_id": "LongYinLiZhiZhuan",
  "dry_run": true,
  "stop_on_error": true,
  "font_metadata_path": "../metadata/fonts_data.tsv",
  "font_display_metadata_path": "../metadata/font_display_info.json",
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

패치가 성공하고 `dry_run`이 `false`이면 `font_display_metadata_path`의 같은 `path_id` 항목을 교체한 폰트 파일명으로 갱신합니다.

## Font Restore Plan

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

## Clothes Patch Plan

```json
{
  "kind": "clothes",
  "dry_run": true,
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
        "size": [940, 2061]
      },
      "assets_file": "D:/Games/.../sharedassets1.assets",
      "png_file": "D:/Mods/.../skeleton_17.png",
      "atlas_file": null,
      "output_assets_file": null,
      "flip_y": false
    }
  ]
}
```

## UI Texture Patch Plan

UI Texture2D는 기존 `.assets` 구조를 바꾸지 않고 DXT5 bytes를 `.resS`에 직접 덮어쓴다.

```json
{
  "kind": "ui_texture",
  "game_id": "LongYinLiZhiZhuan",
  "data_dir": "D:/Games/.../LongYinLiZhiZhuan_Data",
  "dry_run": true,
  "stop_on_error": true,
  "ui_texture_metadata_path": "../metadata/ui_textures.tsv",
  "originals_dir": "../originals",
  "jobs": [
    {
      "path_id": 611,
      "png_file": "../test_inputs/ui_textures/LongYinLiZhiZhuan/611_title_ui.png"
    }
  ]
}
```

## Metadata UI

빌드 전후 모두 다음 옵션으로 TSV 관리 화면을 실행할 수 있다.

```bash
python -m asset_patcher.cli -ui
AssetManager_UnityPy.exe -ui
```

화면에서는 `metadata/data.tsv`와 `metadata/ui_textures.tsv`를 조회, 추가, 수정, 저장한다.

## 문서

- API 계약: `docs/API_contract.md`
- 패키지 상세: `docs/asset_patcher.md`

## 표시용 Font 기본정보

기본 파일은 `metadata/font_display_info.json`입니다.

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

## 원본 보존 위치

```text
originals/{game_id}/textures/{pathID}_{texture_name}.rgba
originals/{game_id}/atlas/{atlas_pathID}_{atlas_name}.txt
originals/{game_id}/fonts/{pathID}_{font_name}.fontdata
```
