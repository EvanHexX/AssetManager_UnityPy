# asset_patcher/modules/texture_unitypy_patch.py
# 설명:
# PNG 크기가 원본 Texture2D와 달라지는 경우 사용하는 UnityPy 기반 Texture2D 패처.
# 목표:
# - PathID 유지
# - Texture name 유지
# - container 변경 방지
# - 대상 Texture2D의 image data만 교체
# - atlas txt는 AtlasManager로 누적 수정

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import UnityPy
from PIL import Image

from asset_patcher.core.atlas_manager import AtlasManager
from asset_patcher.core.texture_metadata import TextureMetadataStore
from asset_patcher.models.patch_request import PatchRequest


@dataclass
class TextureUnityPyPatchResult:
    status: str
    texture_name: str
    path_id: int
    assets_file: str
    png_size: tuple[int, int]
    old_size: tuple[int, int]
    container_unchanged: bool
    atlas_result: dict[str, Any] | None


class TextureUnityPyPatcher:
    """
    크기 변경 PNG를 Texture2D에 반영하는 UnityPy 기반 패처.
    """

    def __init__(
            self,
            texture_metadata_store: TextureMetadataStore,
            atlas_manager: AtlasManager | None = None,
    ) -> None:
        self.texture_metadata_store = texture_metadata_store
        self.atlas_manager = atlas_manager or AtlasManager()

    def patch(
            self,
            request: PatchRequest,
            assets_file: str | Path,
            png_file: str | Path,
            output_file: str | Path | None = None,
            atlas_file: str | Path | None = None,
            dry_run: bool = False,
    ) -> TextureUnityPyPatchResult:
        """
        Texture2D image data를 UnityPy로 교체한다.

        Args:
            request: React/Electron 요청
            assets_file: 원본 .assets 파일
            png_file: 교체할 PNG 파일
            output_file: 저장할 .assets 파일. None이면 원본에 저장
            atlas_file: 수정할 atlas txt 파일
            dry_run: 실제 저장 여부

        Returns:
            TextureUnityPyPatchResult
        """

        assets_file = Path(assets_file)
        png_file = Path(png_file)
        output_file = Path(output_file) if output_file else assets_file

        if not assets_file.exists():
            raise FileNotFoundError(f".assets 파일이 없습니다: {assets_file}")

        if not png_file.exists():
            raise FileNotFoundError(f"PNG 파일이 없습니다: {png_file}")

        metadata = self.texture_metadata_store.find_exact(
            category=request.category,
            gender=request.option1,
            clothes_type=request.option2,
            texture_name=request.texture_name,
            path_id=request.path_id,
            size=request.size,
        )

        with Image.open(png_file) as img:
            new_image = img.convert("RGBA")
            png_size = new_image.size

        env = UnityPy.load(str(assets_file))

        before_container_snapshot = self._snapshot_container(env)

        target_obj = None

        for obj in env.objects:
            if getattr(obj, "path_id", None) == metadata.path_id:
                target_obj = obj
                break

        if target_obj is None:
            raise ValueError(f"Texture2D PathID를 찾지 못했습니다: {metadata.path_id}")

        data = target_obj.read()

        unity_name = getattr(data, "m_Name", None) or getattr(data, "name", None)

        if unity_name != metadata.texture_name:
            raise ValueError(
                f"Texture name 불일치: expected={metadata.texture_name}, actual={unity_name}"
            )

        old_size = (
            int(getattr(data, "m_Width")),
            int(getattr(data, "m_Height")),
        )

        if old_size != metadata.size:
            raise ValueError(
                f"Texture size 불일치: metadata={metadata.size}, unity={old_size}"
            )

        texture_format = str(getattr(data, "m_TextureFormat", ""))

        if metadata.texture_format != "RGBA32":
            raise ValueError(f"현재는 RGBA32만 지원합니다: {metadata.texture_format}")

        # ✅ 핵심 수정: Texture2D 이미지 데이터만 교체한다.
        data.image = new_image
        data.save()

        after_container_snapshot = self._snapshot_container(env)

        container_unchanged = before_container_snapshot == after_container_snapshot

        if not container_unchanged:
            raise ValueError(
                "UnityPy 저장 전후 container snapshot이 변경되었습니다. "
                "안전 문제로 저장을 중단합니다."
            )

        atlas_result = None

        if atlas_file is not None and metadata.atlas_name is not None:
            atlas_result = self.atlas_manager.update_page_for_png(
                atlas_path=atlas_file,
                texture_name=metadata.atlas_page_name,
                png_path=png_file,
            )

        if not dry_run:
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with output_file.open("wb") as f:
                f.write(env.file.save())

        return TextureUnityPyPatchResult(
            status="dry_run" if dry_run else "success",
            texture_name=metadata.texture_name,
            path_id=metadata.path_id,
            assets_file=str(output_file),
            png_size=png_size,
            old_size=old_size,
            container_unchanged=container_unchanged,
            atlas_result=atlas_result,
        )

    def save_atlas_all(self) -> None:
        """
        누적 atlas 변경 사항을 저장한다.
        """

        self.atlas_manager.save_all()

    def _snapshot_container(self, env: Any) -> list[tuple[str, int]]:
        """
        UnityPy env.container를 비교 가능한 형태로 스냅샷한다.

        Args:
            env: UnityPy Environment

        Returns:
            (container_path, path_id) 목록
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
