# UI Texture Patch

## Purpose

`resources.assets` 또는 `sharedassets*.assets` 안의 UI용 `Texture2D` PNG를 교체한다. 기존 의상 patch에서 안정성이 확인된 방식처럼 `.assets` 구조는 변경하지 않고, `m_StreamData`가 가리키는 `.resS` bytes만 직접 교체한다.

## Related Files

- `metadata/ui_textures.tsv`
- `asset_patcher/core/ui_texture_metadata.py`
- `asset_patcher/modules/ui_texture_ress_patch.py`
- `asset_patcher/cli.py`

## Public APIs

CLI plan kind는 `ui_texture`다.

```json
{
  "kind": "ui_texture",
  "game_id": "LongYinLiZhiZhuan",
  "data_dir": "D:/Games/.../LongYinLiZhiZhuan_Data",
  "dry_run": true,
  "ui_texture_metadata_path": "../metadata/ui_textures.tsv",
  "jobs": [
    {
      "path_id": 611,
      "png_file": "../test_inputs/ui_textures/LongYinLiZhiZhuan/611_title_ui.png"
    }
  ]
}
```

## Internal Flow

1. `metadata/ui_textures.tsv`에서 `pathID` 또는 `texture_name` 기준으로 대상 row를 찾는다.
2. `data_dir`와 TSV의 `assets_file`을 조합해 대상 `.assets` 파일을 연다.
3. UnityPy로 `Texture2D`의 `PathID`, name, size, `DXT5`, `m_StreamData`를 검증한다.
4. PNG를 UnityPy `Texture2DConverter.image_to_texture2d(..., DXT5)`로 DXT5 bytes로 인코딩한다.
5. 인코딩 결과 크기가 기존 `m_StreamData.size`와 같을 때만 `.resS`에 overwrite한다.

## Important Constraints

- 현재는 `DXT5`만 지원한다.
- PNG 크기는 TSV의 `width`, `height`와 정확히 같아야 한다.
- `.assets`의 `m_TextureFormat`, stream path, offset, size는 변경하지 않는다.
- `BC7`은 같은 block size라도 `.assets` metadata 변경이 필요하므로 v1에서 제외한다.

## Regression Notes

- 과거 Texture2D를 `.assets` 직접 저장 방식으로 교체했을 때 게임 실행 불가가 발생했다.
- 이 모듈은 같은 실패를 피하기 위해 `.resS` stream bytes만 바꾸는 방식으로 제한한다.

## TODO

- 실제 게임 실행 테스트 결과를 기록한다.
- 필요하면 `DXT1` 등 다른 fixed-size block compression을 별도 whitelist로 추가한다.
