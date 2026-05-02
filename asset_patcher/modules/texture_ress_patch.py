# asset_patcher/modules/texture_ress_patch.py
# 설명:
# UnityPy로 Texture2D 정보를 읽고 검증한 뒤, 실제 PNG 교체는 .resS 파일에 raw RGBA bytes를 직접 덮어쓴다.
# 이 모듈은 container, object path, asset 구조를 변경하지 않는다.
# 단, 현재 안전 버전은 "동일 크기 PNG"만 지원한다.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import UnityPy
from PIL import Image

from asset_patcher.core.atlas_manager import AtlasManager
from asset_patcher.core.texture_metadata import TextureMetadata, TextureMetadataStore
from asset_patcher.models.patch_request import PatchRequest
from asset_patcher.core.original_store import OriginalStore


@dataclass
class TextureRessPatchResult:
    """
    Texture2D .resS 패치 결과를 표현한다.
    """

    status: str
    texture_name: str
    path_id: int
    assets_file: str
    ress_file: str
    stream_offset: int
    stream_size: int
    png_size: tuple[int, int]
    atlas_result: dict[str, Any] | None


class TextureRessPatcher:
    """
    Texture2D .resS 직접 패처.
    """

    def __init__(
            self,
            texture_metadata_store: TextureMetadataStore,
            atlas_manager: AtlasManager | None = None,
            original_store: OriginalStore | None = None,
    ) -> None:
        """
        TextureRessPatcher를 초기화한다.

        Args:
            texture_metadata_store: data.tsv 기반 Texture 메타 저장소
            atlas_manager: atlas 누적 수정 매니저
        """

        self.texture_metadata_store = texture_metadata_store
        self.atlas_manager = atlas_manager or AtlasManager()
        self.original_store = original_store

    def patch(
            self,
            request: PatchRequest,
            assets_file: str | Path,
            png_file: str | Path,
            atlas_file: str | Path | None = None,
            flip_y: bool = True,
            dry_run: bool = False,
    ) -> TextureRessPatchResult:
        """
        단일 Texture2D를 .resS 직접 patch한다.

        Args:
            request: React/Electron에서 전달된 패치 요청
            assets_file: Texture2D가 들어있는 .assets 파일
            png_file: 교체할 PNG 파일
            atlas_file: 필요 시 수정할 atlas txt 파일
            flip_y: raw RGBA 변환 시 상하 반전 여부
            dry_run: 실제 쓰기 없이 검증만 수행

        Returns:
            TextureRessPatchResult

        Raises:
            FileNotFoundError: assets/png/resS 파일이 없을 경우
            ValueError: 메타 불일치, 포맷 불일치, 크기 불일치 등
        """

        assets_file = Path(assets_file)
        png_file = Path(png_file)

        # 입력 파일 존재 여부를 먼저 확인한다.
        if not assets_file.exists():
            raise FileNotFoundError(f".assets 파일이 없습니다: {assets_file}")

        if not png_file.exists():
            raise FileNotFoundError(f"PNG 파일이 없습니다: {png_file}")

        # data.tsv 기준으로 React 요청이 실제 등록된 대상인지 검증한다.
        metadata = self.texture_metadata_store.find_exact(
            category=request.category,
            gender=request.option1,
            clothes_type=request.option2,
            texture_name=request.texture_name,
            path_id=request.path_id,
            size=request.size,
        )

        # PNG를 RGBA raw bytes로 변환한다.
        png_size, raw_rgba = self._load_png_as_rgba_bytes(
            png_file=png_file,
            flip_y=flip_y,
        )

        # 1차 안전 버전에서는 원본 Texture size와 동일한 PNG만 허용한다.
        # PNG 크기가 달라지면 Texture2D width/height 또는 stream size 수정이 필요할 수 있다.
        if png_size != metadata.size:
            raise ValueError(
                "현재 texture_ress_patch 안전 모드는 동일 크기 PNG만 지원합니다. "
                f"metadata_size={metadata.size}, png_size={png_size}, "
                "크기 변경 패치는 UnityPy 최소 수정 모드로 분리해야 합니다."
            )

        # UnityPy로 Texture2D 객체와 stream 정보를 읽는다.
        texture_info = self._read_texture_stream_info(
            assets_file=assets_file,
            metadata=metadata,
        )

        stream_size = texture_info["stream_size"]

        # RGBA32 기준 byte size가 stream size와 정확히 일치해야 안전하게 덮어쓸 수 있다.
        if len(raw_rgba) != stream_size:
            raise ValueError(
                "PNG raw RGBA byte 크기와 Texture2D stream size가 다릅니다. "
                f"raw_size={len(raw_rgba)}, stream_size={stream_size}"
            )

        ress_file = self._resolve_ress_path(
            assets_file=assets_file,
            stream_path=texture_info["stream_path"],
        )

        if not ress_file.exists():
            raise FileNotFoundError(f".resS 파일이 없습니다: {ress_file}")

        atlas_result = None

        # atlas 파일이 있고 metadata에도 atlas가 있으면 atlas 검증/수정을 수행한다.
        # 동일 크기 PNG라면 atlas_manager 내부에서 changed=False가 반환된다.
        if atlas_file is not None and metadata.atlas_name is not None:
            atlas_result = self.atlas_manager.update_page_for_png(
                atlas_path=atlas_file,
                texture_name=metadata.atlas_page_name,
                png_path=png_file,
            )

        # dryRun이면 실제 파일 쓰기와 원본 raw 저장을 하지 않는다.
        if not dry_run:
            # 패치 직전, 현재 .resS에 들어있는 원본 raw bytes를 최초 1회만 저장한다.
            if self.original_store is not None:
                original_raw = self._read_ress_bytes(
                    ress_file=ress_file,
                    offset=texture_info["stream_offset"],
                    size=stream_size,
                )

                if len(original_raw) != stream_size:
                    raise ValueError(
                        f"원본 .resS raw read size 불일치: "
                        f"read={len(original_raw)}, expected={stream_size}"
                    )

                self.original_store.ensure_original_texture_raw(
                    game_id=request.game_id,
                    path_id=metadata.path_id,
                    texture_name=metadata.texture_name,
                    raw_data=original_raw,
                )

            # 원본 raw 저장 후 실제 .resS patch 수행
            self._write_ress_bytes(
                ress_file=ress_file,
                offset=texture_info["stream_offset"],
                data=raw_rgba,
            )

        return TextureRessPatchResult(
            status="dry_run" if dry_run else "success",
            texture_name=metadata.texture_name,
            path_id=metadata.path_id,
            assets_file=str(assets_file),
            ress_file=str(ress_file),
            stream_offset=texture_info["stream_offset"],
            stream_size=stream_size,
            png_size=png_size,
            atlas_result=atlas_result,
        )

    def _read_ress_bytes(
            self,
            ress_file: Path,
            offset: int,
            size: int,
    ) -> bytes:
        """
        .resS 파일에서 원본 raw bytes를 읽는다.
        """

        with ress_file.open("rb") as f:
            f.seek(offset)
            return f.read(size)

    def save_atlas_all(self) -> None:
        """
        누적된 atlas 변경 사항을 저장한다.
        """

        self.atlas_manager.save_all()

    def _read_texture_stream_info(
            self,
            assets_file: Path,
            metadata: TextureMetadata,
    ) -> dict[str, Any]:
        """
        UnityPy로 Texture2D 객체를 읽고, PathID/name/size/format/stream 정보를 검증한다.

        Args:
            assets_file: .assets 파일
            metadata: data.tsv에서 찾은 Texture 메타

        Returns:
            stream 정보 dict

        Raises:
            ValueError: Texture2D를 찾지 못했거나 메타가 불일치하는 경우
        """

        env = UnityPy.load(str(assets_file))

        target_obj = None

        # PathID 기준으로 Texture2D 객체를 찾는다.
        for obj in env.objects:
            if getattr(obj, "path_id", None) == metadata.path_id:
                target_obj = obj
                break

        if target_obj is None:
            raise ValueError(f"Texture2D PathID를 찾지 못했습니다: {metadata.path_id}")

        try:
            data = target_obj.read(check_read=False)
        except TypeError:
            data = target_obj.read()

        # Texture2D name 검증.
        unity_name = getattr(data, "name", None) or getattr(data, "m_Name", None)

        if unity_name != metadata.texture_name:
            raise ValueError(
                f"Texture name 불일치: expected={metadata.texture_name}, actual={unity_name}"
            )

        # Texture2D width/height 검증.
        width = int(getattr(data, "m_Width"))
        height = int(getattr(data, "m_Height"))

        if (width, height) != metadata.size:
            raise ValueError(
                f"Texture size 불일치: expected={metadata.size}, actual={(width, height)}"
            )

        # Texture format 검증.
        texture_format = str(getattr(data, "m_TextureFormat", ""))
        tex_format_text = str(texture_format)

        is_rgba32 = (
                metadata.texture_format == "RGBA32"
                and (
                        tex_format_text == "RGBA32"
                        or tex_format_text == "4"
                        or "RGBA32" in tex_format_text
                )
        )

        if not is_rgba32:
            raise ValueError(
                f"Texture format 불일치 또는 미지원: unity={tex_format_text}, metadata={metadata.texture_format}"
            )

        stream_data = getattr(data, "m_StreamData", None)

        if stream_data is None:
            raise ValueError(f"m_StreamData가 없습니다: pathID={metadata.path_id}")

        stream_path = getattr(stream_data, "path", None)
        stream_offset = int(getattr(stream_data, "offset"))
        stream_size = int(getattr(stream_data, "size"))

        if not stream_path:
            raise ValueError(f"m_StreamData.path가 비어 있습니다: pathID={metadata.path_id}")

        return {
            "stream_path": stream_path,
            "stream_offset": stream_offset,
            "stream_size": stream_size,
        }

    def _resolve_ress_path(self, assets_file: Path, stream_path: str) -> Path:
        """
        Unity Texture2D m_StreamData.path 값을 실제 .resS 파일 경로로 해석한다.

        Args:
            assets_file: .assets 파일 경로
            stream_path: Unity m_StreamData.path

        Returns:
            실제 .resS 파일 경로
        """

        normalized = stream_path.replace("\\", "/")
        filename = Path(normalized).name

        # 대부분의 Unity .resS는 .assets 파일과 같은 폴더에 있다.
        candidate = assets_file.parent / filename

        if candidate.exists():
            return candidate

        # stream_path가 상대 경로인 경우도 고려한다.
        relative_candidate = assets_file.parent / normalized

        if relative_candidate.exists():
            return relative_candidate

        # 존재 여부는 호출부에서 FileNotFoundError로 처리한다.
        return candidate

    def _load_png_as_rgba_bytes(
            self,
            png_file: Path,
            flip_y: bool,
    ) -> tuple[tuple[int, int], bytes]:
        """
        PNG를 RGBA32 raw bytes로 변환한다.

        Args:
            png_file: PNG 파일
            flip_y: 상하 반전 여부

        Returns:
            ((width, height), raw_rgba_bytes)
        """

        with Image.open(png_file) as img:
            rgba = img.convert("RGBA")

            if flip_y:
                rgba = rgba.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

            size = rgba.size
            raw = rgba.tobytes()

        return size, raw

    def _write_ress_bytes(
            self,
            ress_file: Path,
            offset: int,
            data: bytes,
    ) -> None:
        """
        .resS 파일의 지정 offset에 raw bytes를 덮어쓴다.

        Args:
            ress_file: .resS 파일
            offset: stream offset
            data: raw RGBA bytes

        Side Effects:
            ress_file의 일부 byte를 직접 변경한다.
        """

        with ress_file.open("r+b") as f:
            f.seek(offset)
            f.write(data)
