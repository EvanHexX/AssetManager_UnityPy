# asset_patcher/core/original_store.py
# 설명:
# 의상 패치용 원본 PNG, font patch용 원본 폰트 추출물을 보관하는 저장소 유틸리티.
# 히스토리 백업이 아니라 “복원 가능한 원본 소스”만 유지한다.

from __future__ import annotations

import shutil
from pathlib import Path


class OriginalStore:
    """
    원본 PNG/font 보관소를 관리한다.

    기본 구조:
        originals/{game_id}/{category}/{option1}/{option2}/{filename}
    """

    def __init__(self, root_dir: str | Path) -> None:
        """
        OriginalStore를 초기화한다.

        Args:
            root_dir: 원본 보관 루트 폴더
        """

        self.root_dir = Path(root_dir)

    def get_clothes_original_path(
            self,
            game_id: str,
            gender: str,
            clothes_type: str,
            texture_name: str,
    ) -> Path:
        """
        의상 원본 PNG 저장 경로를 반환한다.

        Args:
            game_id: 게임 식별자
            gender: 성별 옵션
            clothes_type: 의상 종류
            texture_name: PNG 파일명

        Returns:
            원본 PNG 저장 경로
        """

        return (
                self.root_dir
                / game_id
                / "clothes"
                / gender
                / clothes_type
                / texture_name
        )

    def ensure_original_png(
            self,
            source_png: str | Path,
            game_id: str,
            gender: str,
            clothes_type: str,
            texture_name: str,
    ) -> Path:
        """
        원본 PNG가 없으면 최초 1회만 저장한다.

        Args:
            source_png: 현재 기준 원본 PNG 파일
            game_id: 게임 식별자
            gender: 성별 옵션
            clothes_type: 의상 종류
            texture_name: PNG 파일명

        Returns:
            보관된 원본 PNG 경로

        Raises:
            FileNotFoundError: source_png가 존재하지 않는 경우
        """

        source_png = Path(source_png)

        # 원본 PNG 파일 존재 여부를 먼저 확인한다.
        if not source_png.exists():
            raise FileNotFoundError(f"원본 PNG 파일이 없습니다: {source_png}")

        original_path = self.get_clothes_original_path(
            game_id=game_id,
            gender=gender,
            clothes_type=clothes_type,
            texture_name=texture_name,
        )

        # 이미 원본이 있으면 덮어쓰지 않는다.
        if original_path.exists():
            return original_path

        # 최초 실행 시에만 원본 PNG를 보관한다.
        original_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_png, original_path)

        return original_path

    def get_font_original_dir(self, game_id: str) -> Path:
        """
        font patch용 원본 폰트 저장 폴더를 반환한다.

        Args:
            game_id: 게임 식별자

        Returns:
            원본 폰트 저장 폴더
        """

        return self.root_dir / game_id / "fonts"

    def has_font_originals(self, game_id: str) -> bool:
        """
        해당 게임의 원본 폰트 추출물이 이미 존재하는지 확인한다.

        Args:
            game_id: 게임 식별자

        Returns:
            원본 폰트 폴더에 파일이 하나 이상 있으면 True
        """

        font_dir = self.get_font_original_dir(game_id)

        if not font_dir.exists():
            return False

        return any(path.is_file() for path in font_dir.iterdir())

    def get_texture_original_path(
            self,
            game_id: str,
            path_id: int,
            texture_name: str,
    ) -> Path:
        """
        Texture .resS 원본 raw bytes 저장 경로를 반환한다.
        """

        safe_name = self._safe_filename(texture_name)

        return (
                self.root_dir
                / game_id
                / "textures"
                / f"{path_id}_{safe_name}.rgba"
        )

    def ensure_original_texture_raw(
            self,
            game_id: str,
            path_id: int,
            texture_name: str,
            raw_data: bytes,
    ) -> bool:
        """
        Texture .resS 원본 raw bytes를 최초 1회만 저장한다.

        Returns:
            새로 저장했으면 True, 이미 있으면 False
        """

        original_path = self.get_texture_original_path(
            game_id=game_id,
            path_id=path_id,
            texture_name=texture_name,
        )

        if original_path.exists():
            return False

        original_path.parent.mkdir(parents=True, exist_ok=True)
        original_path.write_bytes(raw_data)

        return True

    def get_atlas_original_path(
            self,
            game_id: str,
            atlas_path_id: int,
            atlas_name: str,
    ) -> Path:
        """
        atlas TextAsset 원본 txt 저장 경로를 반환한다.
        """

        safe_name = self._safe_filename(atlas_name)

        return (
                self.root_dir
                / game_id
                / "atlas"
                / f"{atlas_path_id}_{safe_name}.txt"
        )

    def ensure_original_atlas_text(
            self,
            game_id: str,
            atlas_path_id: int,
            atlas_name: str,
            text: str,
    ) -> bool:
        """
        atlas TextAsset 원본 txt를 최초 1회만 저장한다.

        Returns:
            새로 저장했으면 True, 이미 있으면 False
        """

        original_path = self.get_atlas_original_path(
            game_id=game_id,
            atlas_path_id=atlas_path_id,
            atlas_name=atlas_name,
        )

        if original_path.exists():
            return False

        original_path.parent.mkdir(parents=True, exist_ok=True)
        original_path.write_text(text, encoding="utf-8")

        return True

    @staticmethod
    def _safe_filename(value: str) -> str:
        """
        파일명에 부적절한 문자를 '_'로 치환한다.
        """

        return "".join(
            ch if ch.isalnum() or ch in ("-", "_", ".") else "_"
            for ch in value
        )
