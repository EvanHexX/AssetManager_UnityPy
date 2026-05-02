# asset_patcher/services/clothes_patch_service.py
# 설명:
# 의상 PNG 패치 요청의 단일 진입점.
# PNG 크기가 원본과 같으면 .resS 직접 패치,
# PNG 크기가 다르면 UnityPy 최소 수정 패치로 자동 분기한다.

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import Image

from asset_patcher.core.atlas_manager import AtlasManager
from asset_patcher.core.texture_metadata import TextureMetadataStore
from asset_patcher.models.patch_request import PatchRequest
from asset_patcher.modules.texture_ress_patch import TextureRessPatcher
from asset_patcher.modules.texture_unitypy_patch import TextureUnityPyPatcher
from asset_patcher.modules.atlas_textasset_patch import AtlasTextAssetPatcher
from asset_patcher.core.original_store import OriginalStore


@dataclass
class ClothesPatchServiceResult:
    """
    의상 패치 서비스 결과.
    """

    status: str
    mode: str
    request: dict[str, Any]
    result: dict[str, Any]


class ClothesPatchService:
    """
    React/Electron에서 전달된 의상 패치 요청을 처리하는 서비스.
    """

    def __init__(
            self,
            texture_metadata_path: str | Path,
            originals_dir: str | Path = "originals",
    ) -> None:
        """
        ClothesPatchService를 초기화한다.

        Args:
            texture_metadata_path: data.tsv 경로
        """

        self.texture_metadata_store = TextureMetadataStore(texture_metadata_path)
        self.original_store = OriginalStore(originals_dir)
        self.atlas_manager = AtlasManager()

        self.ress_patcher = TextureRessPatcher(
            texture_metadata_store=self.texture_metadata_store,
            atlas_manager=self.atlas_manager,
            original_store=self.original_store,
        )

        self.unitypy_patcher = TextureUnityPyPatcher(
            texture_metadata_store=self.texture_metadata_store,
            atlas_manager=self.atlas_manager,
        )

        self.atlas_textasset_patcher = AtlasTextAssetPatcher(
            original_store=self.original_store,
        )

    def patch_one(
            self,
            request_data: dict[str, Any],
            assets_file: str | Path,
            png_file: str | Path,
            atlas_file: str | Path | None = None,
            output_assets_file: str | Path | None = None,
            flip_y: bool = False,
            dry_run: bool = False,
    ) -> ClothesPatchServiceResult:
        """
        단일 의상 PNG 패치 요청을 처리한다.

        Args:
            request_data: React/Electron에서 받은 요청 dict
            assets_file: 대상 .assets 파일
            png_file: 교체할 PNG 파일
            atlas_file: 수정할 atlas txt 파일
            output_assets_file: UnityPy 모드일 때 저장할 .assets 경로
            flip_y: resS patch 시 상하 반전 여부
            dry_run: 실제 저장 여부

        Returns:
            ClothesPatchServiceResult
        """

        request = PatchRequest.from_dict(request_data)

        metadata = self.texture_metadata_store.find_exact(
            category=request.category,
            gender=request.option1,
            clothes_type=request.option2,
            texture_name=request.texture_name,
            path_id=request.path_id,
            size=request.size,
        )

        png_size = self._read_png_size(png_file)

        # atlas 정보가 있는 경우 → 항상 atlas 기준
        if metadata.atlas_name is not None and metadata.atlas_path_id is not None:

            atlas_result = self.atlas_textasset_patcher.patch(
                game_id=request.game_id,
                assets_file=assets_file,
                atlas_path_id=metadata.atlas_path_id,
                atlas_name=metadata.atlas_name,
                texture_name=metadata.atlas_page_name,
                png_file=png_file,
                dry_run=True,
            )

            # 이미 atlas가 PNG와 일치
            if atlas_result.status == "skip":
                result = self.ress_patcher.patch(
                    request=request,
                    assets_file=assets_file,
                    png_file=png_file,
                    atlas_file=None,
                    flip_y=flip_y,
                    dry_run=dry_run,
                )

                return ClothesPatchServiceResult(
                    status=result.status,
                    mode="ress_patch",
                    request=asdict(request),
                    result=asdict(result),
                )

            # atlas 수정 필요
            if not dry_run:
                self.atlas_textasset_patcher.patch(
                    game_id=request.game_id,
                    assets_file=assets_file,
                    atlas_path_id=metadata.atlas_path_id,
                    atlas_name=metadata.atlas_name,
                    texture_name=metadata.atlas_page_name,
                    png_file=png_file,
                    dry_run=False,
                )

            raise ValueError(
                "PNG 크기가 현재 atlas와 다릅니다. "
                "atlas는 수정되었지만 Texture2D 크기 변경 patch는 아직 비활성화되어 있습니다."
            )

        # atlas 없는 경우 → TSV fallback
        if png_size == metadata.size:
            result = self.ress_patcher.patch(
                request=request,
                assets_file=assets_file,
                png_file=png_file,
                atlas_file=None,
                flip_y=flip_y,
                dry_run=dry_run,
            )

            return ClothesPatchServiceResult(
                status=result.status,
                mode="ress_patch",
                request=asdict(request),
                result=asdict(result),
            )

        raise ValueError(
            "PNG 크기가 원본과 다르고 atlas 정보도 없어 처리 불가"
        )

    def save_atlas_all(self) -> None:
        """
        누적된 atlas 변경사항을 저장한다.
        여러 파일 패치 후 마지막에 한 번만 호출한다.
        """

        self.atlas_manager.save_all()

    @staticmethod
    def _read_png_size(png_file: str | Path) -> tuple[int, int]:
        """
        PNG 파일 크기를 읽는다.

        Args:
            png_file: PNG 파일 경로

        Returns:
            (width, height)
        """

        png_file = Path(png_file)

        if not png_file.exists():
            raise FileNotFoundError(f"PNG 파일이 없습니다: {png_file}")

        with Image.open(png_file) as img:
            return img.size
