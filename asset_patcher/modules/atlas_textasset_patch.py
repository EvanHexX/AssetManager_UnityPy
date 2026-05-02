# asset_patcher/modules/atlas_textasset_patch.py
# 설명:
# Unity assets 내부 TextAsset 형태의 Spine atlas txt를 PathID 기준으로 찾아 수정한다.
# 외부 atlas_file 없이 atlas_pathID만으로 현재 atlas 내용을 읽고, size/bounds/offsets를 PNG 크기에 맞춰 수정한다.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import UnityPy
from PIL import Image

from asset_patcher.core.atlas_manager import AtlasManager
from asset_patcher.core.original_store import OriginalStore


@dataclass
class AtlasTextAssetPatchResult:
    """
    TextAsset atlas patch 결과.
    """

    status: str
    atlas_path_id: int
    texture_name: str
    old_size: tuple[int, int]
    new_size: tuple[int, int]
    changed: bool
    assets_file: str
    output_file: str | None
    container_unchanged: bool


class AtlasTextAssetPatcher:
    """
    TextAsset atlas를 PathID 기준으로 수정하는 패처.
    """

    def __init__(self, original_store: OriginalStore | None = None) -> None:
        """
        AtlasTextAssetPatcher를 초기화한다.
        """

        self.atlas_manager = AtlasManager()
        self.original_store = original_store

    def patch(
            self,
            game_id: str,
            assets_file: str | Path,
            atlas_path_id: int,
            atlas_name: str,
            texture_name: str,
            png_file: str | Path,
            output_assets_file: str | Path | None = None,
            dry_run: bool = False,
    ) -> AtlasTextAssetPatchResult:
        """
        TextAsset atlas를 PNG 크기에 맞춰 수정한다.

        Args:
            assets_file: atlas TextAsset이 들어있는 .assets 파일
            atlas_path_id: data.tsv의 atlas_pathID
            texture_name: atlas page 이름. 예: skeleton_17 또는 skeleton_17.png
            png_file: 새 PNG 파일
            output_assets_file: 저장할 .assets 경로. None이면 원본 덮어쓰기
            dry_run: 실제 저장 여부

        Returns:
            AtlasTextAssetPatchResult
        """

        assets_file = Path(assets_file)
        png_file = Path(png_file)
        output_path = Path(output_assets_file) if output_assets_file else None

        if not assets_file.exists():
            raise FileNotFoundError(f"atlas assets 파일이 없습니다: {assets_file}")

        if not png_file.exists():
            raise FileNotFoundError(f"PNG 파일이 없습니다: {png_file}")

        page_name = self._normalize_page_name(texture_name)

        with Image.open(png_file) as img:
            new_size = img.size

        env = UnityPy.load(str(assets_file))
        before_container = self._snapshot_container(env)

        target_obj = self._find_object_by_path_id(env, atlas_path_id)

        if target_obj is None:
            raise ValueError(f"atlas TextAsset PathID를 찾지 못했습니다: {atlas_path_id}")

        type_name = getattr(target_obj.type, "name", None)

        if type_name != "TextAsset":
            raise ValueError(
                f"atlas PathID가 TextAsset이 아닙니다: pathID={atlas_path_id}, type={type_name}"
            )

        data = target_obj.read()

        original_text = self._get_textasset_text(data)
        if self.original_store is not None:
            self.original_store.ensure_original_atlas_text(
                game_id=game_id,
                atlas_path_id=atlas_path_id,
                atlas_name=atlas_name,
                text=original_text,
            )
        document = self.atlas_manager.parse_text(original_text)

        old_size = document.get_page_size(page_name)

        if old_size == new_size:
            return AtlasTextAssetPatchResult(
                status="skip",
                atlas_path_id=atlas_path_id,
                texture_name=page_name,
                old_size=old_size,
                new_size=new_size,
                changed=False,
                assets_file=str(assets_file),
                output_file=str(output_path) if output_path else None,
                container_unchanged=True,
            )

        # ✅ AtlasDocument.update_page_for_png는 현재 atlas page size 기준으로 배율 계산한다.
        patch_result = document.update_page_for_png(
            texture_name=page_name,
            png_path=png_file,
        )

        new_text = document.to_text()

        self._set_textasset_text(data, new_text)
        data.save()

        after_container = self._snapshot_container(env)
        container_unchanged = before_container == after_container

        if not container_unchanged:
            raise ValueError(
                "Atlas TextAsset 저장 전후 container snapshot이 변경되었습니다. "
                "안전 문제로 저장을 중단합니다."
            )

        if not dry_run:
            save_path = output_path or assets_file
            save_path.parent.mkdir(parents=True, exist_ok=True)

            with save_path.open("wb") as f:
                f.write(env.file.save())

        return AtlasTextAssetPatchResult(
            status="dry_run" if dry_run else "success",
            atlas_path_id=atlas_path_id,
            texture_name=page_name,
            old_size=old_size,
            new_size=new_size,
            changed=bool(patch_result.get("changed")),
            assets_file=str(assets_file),
            output_file=str(output_path) if output_path else str(assets_file),
            container_unchanged=container_unchanged,
        )

    @staticmethod
    def _normalize_page_name(texture_name: str) -> str:
        """
        skeleton_17 또는 skeleton_17.png를 atlas page 이름으로 정규화한다.
        """

        value = texture_name.strip()

        if value.lower().endswith(".png"):
            return value

        return f"{value}.png"

    @staticmethod
    def _find_object_by_path_id(env: Any, path_id: int) -> Any | None:
        """
        UnityPy env에서 PathID 기준 object를 찾는다.
        """

        for obj in env.objects:
            if getattr(obj, "path_id", None) == int(path_id):
                return obj

        return None

    @staticmethod
    def _get_textasset_text(data: Any) -> str:
        """
        Unity TextAsset에서 문자열 내용을 읽는다.
        UnityPy 버전에 따라 script 또는 m_Script일 수 있다.
        """

        value = None

        if hasattr(data, "script"):
            value = getattr(data, "script")
        elif hasattr(data, "m_Script"):
            value = getattr(data, "m_Script")

        if value is None:
            raise ValueError("TextAsset script/m_Script 필드를 찾지 못했습니다.")

        if isinstance(value, str):
            return value

        if isinstance(value, bytes):
            return value.decode("utf-8")

        if isinstance(value, bytearray):
            return bytes(value).decode("utf-8")

        raise ValueError(f"지원하지 않는 TextAsset script 타입입니다: {type(value).__name__}")

    @staticmethod
    def _set_textasset_text(data: Any, text: str) -> None:
        """
        Unity TextAsset 문자열 내용을 다시 설정한다.
        기존 필드 타입을 최대한 유지한다.
        """

        if hasattr(data, "script"):
            current = getattr(data, "script")

            if isinstance(current, str):
                setattr(data, "script", text)
            else:
                setattr(data, "script", text.encode("utf-8"))

            return

        if hasattr(data, "m_Script"):
            current = getattr(data, "m_Script")

            if isinstance(current, str):
                setattr(data, "m_Script", text)
            else:
                setattr(data, "m_Script", text.encode("utf-8"))

            return

        raise ValueError("TextAsset script/m_Script 필드를 찾지 못했습니다.")

    @staticmethod
    def _snapshot_container(env: Any) -> list[tuple[str, int]]:
        """
        UnityPy env.container를 비교 가능한 형태로 스냅샷한다.
        """

        snapshot: list[tuple[str, int]] = []
        container = getattr(env, "container", None)

        if not container:
            return snapshot

        for key, obj in container.items():
            path_id = getattr(obj, "path_id", None)

            if path_id is None and hasattr(obj, "object_reader"):
                path_id = getattr(obj.object_reader, "path_id", None)

            snapshot.append((str(key), int(path_id) if path_id is not None else -1))

        return sorted(snapshot)
