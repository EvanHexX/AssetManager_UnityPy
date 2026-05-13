# asset_patcher/modules/ui_texture_ress_patch.py
# 설명:
# DXT5 UI Texture2D를 기존 .assets 구조 변경 없이 .resS stream bytes만 직접 교체한다.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import UnityPy
import etcpak
from PIL import Image
from UnityPy.enums import TextureFormat

from asset_patcher.core.original_store import OriginalStore
from asset_patcher.core.ui_texture_metadata import UiTextureMetadata, UiTextureMetadataStore


@dataclass
class UiTextureRessPatchResult:
    status: str
    texture_name: str
    path_id: int
    assets_file: str
    ress_file: str
    stream_offset: int
    stream_size: int
    png_size: tuple[int, int]
    encoded_size: int
    texture_format: str


class UiTextureRessPatcher:
    """
    UI Texture2D용 .resS 직접 패처.
    """

    def __init__(
        self,
        metadata_store: UiTextureMetadataStore,
        original_store: OriginalStore,
    ) -> None:
        self.metadata_store = metadata_store
        self.original_store = original_store

    def patch(
        self,
        game_id: str,
        data_dir: str | Path,
        png_file: str | Path,
        path_id: int | None = None,
        texture_name: str | None = None,
        dry_run: bool = False,
        flip_y: bool | None = None,
    ) -> UiTextureRessPatchResult:
        metadata = self.metadata_store.find(path_id=path_id, texture_name=texture_name)
        data_dir = Path(data_dir)
        assets_file = self._resolve_assets_file(data_dir=data_dir, metadata=metadata)
        png_file = Path(png_file)

        if not assets_file.exists():
            raise FileNotFoundError(f".assets 파일이 없습니다: {assets_file}")

        if not png_file.exists():
            raise FileNotFoundError(f"PNG 파일이 없습니다: {png_file}")

        if metadata.texture_format != "DXT5":
            raise ValueError(f"현재 UI texture patch는 DXT5만 지원합니다: {metadata.texture_format}")

        with Image.open(png_file) as img:
            new_image = img.convert("RGBA")
            png_size = new_image.size

        if png_size != metadata.size:
            raise ValueError(
                f"PNG 크기 불일치: metadata={metadata.size}, png={png_size}"
            )

        texture_info = self._read_texture_stream_info(assets_file=assets_file, metadata=metadata)
        do_flip = metadata.flip_y if flip_y is None else flip_y
        encoded_bytes = self._encode_dxt5(new_image, flip_y=do_flip)

        stream_size = texture_info["stream_size"]

        if len(encoded_bytes) != stream_size:
            raise ValueError(
                "DXT5 encoded byte 크기와 Texture2D stream size가 다릅니다. "
                f"encoded={len(encoded_bytes)}, stream_size={stream_size}"
            )

        ress_file = self._resolve_ress_path(
            assets_file=assets_file,
            stream_path=texture_info["stream_path"],
        )

        if not ress_file.exists():
            raise FileNotFoundError(f".resS 파일이 없습니다: {ress_file}")

        if not dry_run:
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

            self.original_store.ensure_original_ui_texture_raw(
                game_id=game_id,
                path_id=metadata.path_id,
                texture_name=metadata.texture_name,
                raw_data=original_raw,
                extension="dxt5",
            )

            self._write_ress_bytes(
                ress_file=ress_file,
                offset=texture_info["stream_offset"],
                data=encoded_bytes,
            )

        return UiTextureRessPatchResult(
            status="dry_run" if dry_run else "success",
            texture_name=metadata.texture_name,
            path_id=metadata.path_id,
            assets_file=str(assets_file),
            ress_file=str(ress_file),
            stream_offset=texture_info["stream_offset"],
            stream_size=stream_size,
            png_size=png_size,
            encoded_size=len(encoded_bytes),
            texture_format=metadata.texture_format,
        )

    def _read_texture_stream_info(
        self,
        assets_file: Path,
        metadata: UiTextureMetadata,
    ) -> dict[str, Any]:
        env = UnityPy.load(str(assets_file))
        target_obj = None

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

        unity_name = getattr(data, "name", None) or getattr(data, "m_Name", None)

        if unity_name != metadata.texture_name:
            raise ValueError(
                f"Texture name 불일치: expected={metadata.texture_name}, actual={unity_name}"
            )

        size = (int(getattr(data, "m_Width")), int(getattr(data, "m_Height")))

        if size != metadata.size:
            raise ValueError(f"Texture size 불일치: expected={metadata.size}, actual={size}")

        texture_format = TextureFormat(int(getattr(data, "m_TextureFormat")))

        if texture_format != TextureFormat.DXT5:
            raise ValueError(f"Texture format 불일치 또는 미지원: unity={texture_format.name}")

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

    def _encode_dxt5(self, image: Image.Image, flip_y: bool) -> bytes:
        """
        PNG RGBA pixels를 DXT5/BC3 bytes로 인코딩한다.
        UnityPy의 DXT5 경로와 같은 etcpak.compress_bc3를 직접 사용해 불필요한 export 의존성을 피한다.
        """

        if flip_y:
            image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

        width, height = image.size

        if width % 4 != 0 or height % 4 != 0:
            raise ValueError(f"DXT5 texture 크기는 4의 배수여야 합니다: {(width, height)}")

        return etcpak.compress_bc3(image.tobytes("raw", "RGBA"), width, height)

    def _resolve_assets_file(self, data_dir: Path, metadata: UiTextureMetadata) -> Path:
        assets_path = Path(metadata.assets_file)

        if assets_path.is_absolute():
            return assets_path

        return data_dir / assets_path

    def _resolve_ress_path(self, assets_file: Path, stream_path: str) -> Path:
        normalized = stream_path.replace("\\", "/")
        filename = Path(normalized).name
        candidate = assets_file.parent / filename

        if candidate.exists():
            return candidate

        relative_candidate = assets_file.parent / normalized

        if relative_candidate.exists():
            return relative_candidate

        return candidate

    def _read_ress_bytes(self, ress_file: Path, offset: int, size: int) -> bytes:
        with ress_file.open("rb") as f:
            f.seek(offset)
            return f.read(size)

    def _write_ress_bytes(self, ress_file: Path, offset: int, data: bytes) -> None:
        with ress_file.open("r+b") as f:
            f.seek(offset)
            f.write(data)
