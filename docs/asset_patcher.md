# asset_patcher

`asset_patcher`는 UnityPy를 사용해 Unity asset 파일의 Texture2D, Spine atlas, Font 리소스를 패치하는 Python 패키지다.

## Entry Point

```bash
python -m asset_patcher.cli --plan ./examples/clothes_patch.example.json --report ./reports/report.json
```

빌드된 exe를 사용할 때도 입력 계약은 같다.

```bash
AssetManager_UnityPy.exe --plan patch_plan.json --report patch_report.json
```

## Plan Kinds

```text
kind=clothes       의상 Texture2D/atlas 패치
kind=font_list     현재 Font PathID와 추출 파일명 조회
kind=font_extract  원본 Font data 추출
kind=font          Font data 교체
kind=font_restore  원본 Font data 복원
```

## Font List

`resources.assets` 내부의 현재 Font 객체를 조회하고 PathID와 추출 파일명만 출력한다. 파일을 저장하거나 수정하지 않는다.

```json
{
  "kind": "font_list",
  "font_display_metadata_path": "../metadata/font_display_info.json",
  "assets_file": "D:/Games/.../resources.assets"
}
```

출력:

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

`font_display_metadata_path`를 지정하면 표시용 JSON도 함께 동기화한다. 동기화된 파일명은 `2418_SourceHanSerifCN-Medium.fontdata`가 아니라 `SourceHanSerifCN-Medium.otf` 형식이다.

## Font Extract

`fonts_data.tsv`에 등록된 Font 원본 data를 `originals/{game_id}/fonts` 아래에 저장한다.

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

## Font Patch

Font 이름은 중복될 수 있으므로 실사용에서는 `path_id` 기준 패치를 권장한다.

```json
{
  "kind": "font",
  "game_id": "LongYinLiZhiZhuan",
  "dry_run": false,
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

패치가 성공하고 `dry_run`이 `false`이면 표시용 JSON의 같은 `path_id` 항목이 교체 폰트 파일명으로 갱신된다.

## Font Restore

```json
{
  "kind": "font_restore",
  "game_id": "LongYinLiZhiZhuan",
  "dry_run": false,
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

## Clothes Patch

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

## Metadata

`metadata/data.tsv`는 Texture2D 패치 대상 기준 데이터다.

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

`metadata/fonts_data.tsv`는 Font 패치 대상 기준 데이터다.

필수 컬럼:

```text
Name
Description
Type
PathID
Source
```

## Safety Checks

```text
PathID 검증
Texture name/size/format 검증
.resS stream size 검증
UnityPy 저장 전후 container snapshot 검증
atlas 원본 최초 1회 보존
font 원본 data 최초 1회 보존
dry_run 지원
```
