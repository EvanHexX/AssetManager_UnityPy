# Project Map

## Purpose

이 문서는 사람이 말하는 기능 이름을 실제 파일 위치로 빠르게 연결하기 위한 project memory다.

## Modules

- CLI entrypoint → `asset_patcher/cli.py`
- Outfit Texture patch → `asset_patcher/services/clothes_patch_service.py`, `asset_patcher/modules/texture_ress_patch.py`
- Outfit Texture metadata → `metadata/data.tsv`, `asset_patcher/core/texture_metadata.py`
- UI Texture patch → `asset_patcher/modules/ui_texture_ress_patch.py`
- UI Texture metadata → `metadata/ui_textures.tsv`, `asset_patcher/core/ui_texture_metadata.py`
- Metadata editor UI → `asset_patcher/ui/tsv_editor.py`
- Font patch → `asset_patcher/modules/font_patch.py`
- Original backup store → `asset_patcher/core/original_store.py`

