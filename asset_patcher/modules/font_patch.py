# asset_patcher/modules/font_patch.py
# 설명:
# resources.assets 내부 Font 객체의 font data만 교체한다.
# 첫 실행 시 원본 Font 데이터를 originals/{game_id}/fonts 에 추출해 보관한다.
# 대상 Font는 fonts_data.tsv의 PathID 기준으로 검증한다.

from __future__ import annotations

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


@dataclass
class FontDataRef:
    """
    Unity Font 객체 안의 font data 필드 참조 정보.
    """

    field_name: str
    value_type: str
    data: bytes


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
        이름 중복 가능성이 있으면 font_metadata.py에서 실패 처리한다.
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

        before_path_id = getattr(target_obj, "path_id", None)

        font_ref = self._get_font_data_ref(data)

        original_saved = self._ensure_original_font_saved(
            game_id=game_id,
            path_id=metadata.path_id,
            font_name=metadata.name,
            old_font_data=font_ref.data,
        )

        self._set_font_data_from_ref(
            data=data,
            font_ref=font_ref,
            font_bytes=replacement_bytes,
        )

        data.save()

        after_container = self._snapshot_container(env)
        container_unchanged = before_container == after_container

        if not container_unchanged:
            raise ValueError(
                "UnityPy 저장 전후 container snapshot이 변경되었습니다. "
                "안전 문제로 저장을 중단합니다."
            )

        after_obj = self._find_object_by_path_id(env, metadata.path_id)

        if after_obj is None:
            raise ValueError(
                f"Font 저장 후 PathID를 다시 찾지 못했습니다: {metadata.path_id}"
            )

        after_path_id = getattr(after_obj, "path_id", None)

        if before_path_id != after_path_id:
            raise ValueError(
                f"Font PathID 변경 감지: before={before_path_id}, after={after_path_id}"
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
            old_data_size=len(font_ref.data),
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

            try:
                font_ref = self._get_font_data_ref(data)
            except ValueError as exc:
                results.append(
                    {
                        "font_name": metadata.name,
                        "path_id": metadata.path_id,
                        "status": "no_font_data",
                        "message": str(exc),
                    }
                )
                continue

            output_path = font_dir / self._build_original_font_filename(
                path_id=metadata.path_id,
                font_name=metadata.name,
            )

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

            output_path.write_bytes(font_ref.data)

            results.append(
                {
                    "font_name": metadata.name,
                    "path_id": metadata.path_id,
                    "status": "saved",
                    "field_name": font_ref.field_name,
                    "value_type": font_ref.value_type,
                    "path": str(output_path),
                    "size": len(font_ref.data),
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
            / self._build_original_font_filename(
                path_id=metadata.path_id,
                font_name=metadata.name,
            )
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
        path_id: int,
        font_name: str,
        old_font_data: bytes,
    ) -> bool:
        """
        원본 Font 데이터를 최초 1회만 저장한다.
        """

        font_dir = self.original_store.get_font_original_dir(game_id)
        font_dir.mkdir(parents=True, exist_ok=True)

        original_path = font_dir / self._build_original_font_filename(
            path_id=path_id,
            font_name=font_name,
        )

        if original_path.exists():
            return False

        original_path.write_bytes(old_font_data)
        return True

    @staticmethod
    def _build_original_font_filename(path_id: int, font_name: str) -> str:
        """
        원본 Font 저장 파일명을 만든다.
        파일명에 부적절한 문자는 '_'로 치환한다.
        """

        safe_name = "".join(
            ch if ch.isalnum() or ch in ("-", "_", ".") else "_"
            for ch in font_name
        )

        return f"{path_id}_{safe_name}.fontdata"

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
    def _get_font_data_ref(data: Any) -> FontDataRef:
        """
        Unity Font 객체에서 font data bytes와 필드 정보를 찾는다.
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

            converted = FontPatcher._to_bytes_or_none(value)

            if converted is None:
                continue

            return FontDataRef(
                field_name=field,
                value_type=type(value).__name__,
                data=converted,
            )

        # ✅ 일부 UnityPy 버전에서는 typetree dict로 접근해야 할 수 있다.
        try:
            tree = data.read_typetree()
        except Exception:
            tree = None

        if isinstance(tree, dict):
            for field in candidate_fields:
                if field not in tree:
                    continue

                converted = FontPatcher._to_bytes_or_none(tree[field])

                if converted is None:
                    continue

                return FontDataRef(
                    field_name=field,
                    value_type=f"typetree:{type(tree[field]).__name__}",
                    data=converted,
                )

        raise ValueError("Font data 필드를 찾지 못했습니다.")

    @staticmethod
    def _set_font_data_from_ref(
        data: Any,
        font_ref: FontDataRef,
        font_bytes: bytes,
    ) -> None:
        """
        FontDataRef의 필드 정보를 기준으로 Font data를 교체한다.
        """

        field = font_ref.field_name

        if not hasattr(data, field):
            raise ValueError(f"Font data 필드가 data 객체에 없습니다: {field}")

        current = getattr(data, field)

        # ✅ 기존 타입을 최대한 유지한다.
        if isinstance(current, bytearray):
            setattr(data, field, bytearray(font_bytes))
            return

        if isinstance(current, list):
            setattr(data, field, list(font_bytes))
            return

        if isinstance(current, tuple):
            setattr(data, field, tuple(font_bytes))
            return

        setattr(data, field, font_bytes)

    @staticmethod
    def _to_bytes_or_none(value: Any) -> bytes | None:
        """
        다양한 bytes 유사 값을 bytes로 변환한다.
        """

        if value is None:
            return None

        if isinstance(value, bytes):
            return value

        if isinstance(value, bytearray):
            return bytes(value)

        if isinstance(value, memoryview):
            return value.tobytes()

        if isinstance(value, list):
            try:
                return bytes(value)
            except Exception:
                return None

        if isinstance(value, tuple):
            try:
                return bytes(value)
            except Exception:
                return None

        return None

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