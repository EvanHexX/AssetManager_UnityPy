# asset_patcher/modules/font_patch.py
# 설명:
# resources.assets 내부 Font 객체의 font data만 교체한다.
# 첫 실행 시 원본 Font 데이터를 originals/{game_id}/fonts 에 추출해 보관한다.
# 대상 Font는 fonts_data.tsv의 PathID 기준으로 검증한다.

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import UnityPy

from asset_patcher.core.font_metadata import FontMetadataStore
from asset_patcher.core.original_store import OriginalStore


@dataclass
class FontPatchResult:
    status: str
    game_id: str
    font_name: str
    path_id: int
    assets_file: str
    replacement_file: str
    output_file: str
    original_saved: bool
    container_unchanged: bool
    old_data_size: int
    new_data_size: int


class FontPatcher:
    """
    resources.assets 내부 Font 데이터를 교체하는 패처.
    """

    def __init__(
            self,
            font_metadata_store: FontMetadataStore,
            original_store: OriginalStore,
    ) -> None:
        self.font_metadata_store = font_metadata_store
        self.original_store = original_store

    def patch_by_name(
            self,
            game_id: str,
            font_name: str,
            assets_file: str | Path,
            replacement_font_file: str | Path,
            output_file: str | Path | None = None,
            dry_run: bool = False,
    ) -> FontPatchResult:
        """
        Font 이름 기준으로 Font 데이터를 교체한다.
        실제 대상은 fonts_data.tsv의 PathID로 확정한다.
        """

        metadata = self.font_metadata_store.find_by_name(font_name)

        return self.patch_by_path_id(
            game_id=game_id,
            path_id=metadata.path_id,
            assets_file=assets_file,
            replacement_font_file=replacement_font_file,
            output_file=output_file,
            dry_run=dry_run,
        )

    def patch_by_path_id(
            self,
            game_id: str,
            path_id: int,
            assets_file: str | Path,
            replacement_font_file: str | Path,
            output_file: str | Path | None = None,
            dry_run: bool = False,
    ) -> FontPatchResult:
        """
        Font PathID 기준으로 Font 데이터를 교체한다.

        Args:
            game_id: 게임 식별자
            path_id: fonts_data.tsv의 Font PathID
            assets_file: resources.assets 경로
            replacement_font_file: 교체할 ttf/otf 파일
            output_file: 저장할 resources.assets 경로. None이면 원본 덮어쓰기
            dry_run: 실제 저장 없이 검증만 수행

        Returns:
            FontPatchResult
        """

        metadata = self.font_metadata_store.find_by_path_id(path_id)

        assets_file = Path(assets_file)
        replacement_font_file = Path(replacement_font_file)
        output_file = Path(output_file) if output_file else assets_file

        if not assets_file.exists():
            raise FileNotFoundError(f"resources.assets 파일이 없습니다: {assets_file}")

        if not replacement_font_file.exists():
            raise FileNotFoundError(f"교체 Font 파일이 없습니다: {replacement_font_file}")

        replacement_bytes = replacement_font_file.read_bytes()

        env = UnityPy.load(str(assets_file))
        before_container = self._snapshot_container(env)

        target_obj = self._find_object_by_path_id(env, metadata.path_id)

        if target_obj is None:
            raise ValueError(f"Font PathID를 찾지 못했습니다: {metadata.path_id}")

        data = target_obj.read()

        unity_name = getattr(data, "m_Name", None) or getattr(data, "name", None)

        if unity_name != metadata.name:
            raise ValueError(
                f"Font name 불일치: expected={metadata.name}, actual={unity_name}"
            )

        old_font_data = self._get_font_data(data)

        if old_font_data is None:
            raise ValueError(
                f"Font data 필드를 찾지 못했습니다: name={metadata.name}, pathID={metadata.path_id}"
            )

        original_saved = self._ensure_original_font_saved(
            game_id=game_id,
            font_name=metadata.name,
            old_font_data=old_font_data,
        )

        # 핵심 수정: Font 객체 전체가 아니라 font data 필드만 교체한다.
        self._set_font_data(data, replacement_bytes)
        data.save()

        after_container = self._snapshot_container(env)
        container_unchanged = before_container == after_container

        if not container_unchanged:
            raise ValueError(
                "UnityPy 저장 전후 container snapshot이 변경되었습니다. "
                "안전 문제로 저장을 중단합니다."
            )

        if not dry_run:
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with output_file.open("wb") as f:
                f.write(env.file.save())

        return FontPatchResult(
            status="dry_run" if dry_run else "success",
            game_id=game_id,
            font_name=metadata.name,
            path_id=metadata.path_id,
            assets_file=str(assets_file),
            replacement_file=str(replacement_font_file),
            output_file=str(output_file),
            original_saved=original_saved,
            container_unchanged=container_unchanged,
            old_data_size=len(old_font_data),
            new_data_size=len(replacement_bytes),
        )

    def extract_originals(
            self,
            game_id: str,
            assets_file: str | Path,
            overwrite: bool = False,
    ) -> list[dict[str, Any]]:
        """
        fonts_data.tsv에 등록된 모든 Font 원본 데이터를 추출한다.
        Arial도 TSV에 있으면 추출 대상에 포함된다.
        """

        assets_file = Path(assets_file)

        if not assets_file.exists():
            raise FileNotFoundError(f"resources.assets 파일이 없습니다: {assets_file}")

        env = UnityPy.load(str(assets_file))
        results: list[dict[str, Any]] = []

        font_dir = self.original_store.get_font_original_dir(game_id)
        font_dir.mkdir(parents=True, exist_ok=True)

        for metadata in self.font_metadata_store.list_all():
            target_obj = self._find_object_by_path_id(env, metadata.path_id)

            if target_obj is None:
                results.append(
                    {
                        "font_name": metadata.name,
                        "path_id": metadata.path_id,
                        "status": "missing",
                    }
                )
                continue

            data = target_obj.read()
            font_data = self._get_font_data(data)

            if font_data is None:
                results.append(
                    {
                        "font_name": metadata.name,
                        "path_id": metadata.path_id,
                        "status": "no_font_data",
                    }
                )
                continue

            output_path = font_dir / f"{metadata.path_id}_{metadata.name}.fontdata"

            if output_path.exists() and not overwrite:
                results.append(
                    {
                        "font_name": metadata.name,
                        "path_id": metadata.path_id,
                        "status": "exists",
                        "path": str(output_path),
                    }
                )
                continue

            output_path.write_bytes(font_data)

            results.append(
                {
                    "font_name": metadata.name,
                    "path_id": metadata.path_id,
                    "status": "saved",
                    "path": str(output_path),
                    "size": len(font_data),
                }
            )

        return results

    def restore_by_path_id(
            self,
            game_id: str,
            path_id: int,
            assets_file: str | Path,
            output_file: str | Path | None = None,
            dry_run: bool = False,
    ) -> FontPatchResult:
        """
        originals에 저장된 원본 Font 데이터로 복원한다.
        """

        metadata = self.font_metadata_store.find_by_path_id(path_id)
        original_path = (
                self.original_store.get_font_original_dir(game_id)
                / f"{metadata.path_id}_{metadata.name}.fontdata"
        )

        if not original_path.exists():
            raise FileNotFoundError(f"저장된 원본 Font 데이터가 없습니다: {original_path}")

        return self.patch_by_path_id(
            game_id=game_id,
            path_id=path_id,
            assets_file=assets_file,
            replacement_font_file=original_path,
            output_file=output_file,
            dry_run=dry_run,
        )

    def _ensure_original_font_saved(
            self,
            game_id: str,
            font_name: str,
            old_font_data: bytes,
    ) -> bool:
        """
        원본 Font 데이터를 최초 1회만 저장한다.
        """

        font_dir = self.original_store.get_font_original_dir(game_id)
        font_dir.mkdir(parents=True, exist_ok=True)

        metadata = self.font_metadata_store.find_by_name(font_name)
        original_path = font_dir / f"{metadata.path_id}_{metadata.name}.fontdata"

        if original_path.exists():
            return False

        original_path.write_bytes(old_font_data)
        return True

    @staticmethod
    def _find_object_by_path_id(env: Any, path_id: int) -> Any | None:
        """
        UnityPy env에서 PathID 기준 object를 찾는다.
        """

        for obj in env.objects:
            if getattr(obj, "path_id", None) == path_id:
                return obj

        return None

    @staticmethod
    def _get_font_data(data: Any) -> bytes | None:
        """
        Unity Font 객체에서 font data bytes를 읽는다.
        UnityPy/Unity 버전에 따라 필드명이 다를 수 있어 후보를 순서대로 확인한다.
        """

        candidate_fields = [
            "m_FontData",
            "font_data",
            "m_FontDataArray",
        ]

        for field in candidate_fields:
            if not hasattr(data, field):
                continue

            value = getattr(data, field)

            if value is None:
                continue

            if isinstance(value, bytes):
                return value

            if isinstance(value, bytearray):
                return bytes(value)

            if isinstance(value, list):
                try:
                    return bytes(value)
                except Exception:
                    continue

        return None

    @staticmethod
    def _set_font_data(data: Any, font_bytes: bytes) -> None:
        """
        Unity Font 객체의 font data 필드만 교체한다.
        """

        candidate_fields = [
            "m_FontData",
            "font_data",
            "m_FontDataArray",
        ]

        for field in candidate_fields:
            if not hasattr(data, field):
                continue

            current = getattr(data, field)

            if isinstance(current, bytearray):
                setattr(data, field, bytearray(font_bytes))
                return

            if isinstance(current, list):
                setattr(data, field, list(font_bytes))
                return

            setattr(data, field, font_bytes)
            return

        raise ValueError("교체 가능한 Font data 필드를 찾지 못했습니다.")

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
