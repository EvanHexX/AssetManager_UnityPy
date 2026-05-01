# asset_patcher/core/game_metadata.py
# 설명:
# game_id/category/option1/option2 기준으로 패치에 필요한 메타데이터를 조회한다.
# 현재는 의상 atlas txt 경로 조회를 우선 지원한다.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class GameMetadataStore:
    """
    게임별 패치 메타데이터를 로드하고 조회한다.
    """

    def __init__(self, metadata_dir: str | Path) -> None:
        """
        GameMetadataStore를 초기화한다.

        Args:
            metadata_dir: 게임 메타 JSON들이 들어있는 폴더
        """

        self.metadata_dir = Path(metadata_dir)
        self._cache: dict[str, dict[str, Any]] = {}

    def load_game_metadata(self, game_id: str) -> dict[str, Any]:
        """
        game_id에 해당하는 메타 JSON을 로드한다.

        Args:
            game_id: 게임 식별자

        Returns:
            게임 메타데이터 dict

        Raises:
            FileNotFoundError: 메타 파일이 없을 경우
            ValueError: JSON의 game_id가 요청 game_id와 다를 경우
        """

        # 같은 실행 중에는 메타 파일을 중복 로드하지 않는다.
        if game_id in self._cache:
            return self._cache[game_id]

        metadata_path = self.metadata_dir / f"{game_id}.json"

        if not metadata_path.exists():
            raise FileNotFoundError(f"게임 메타 파일이 없습니다: {metadata_path}")

        with metadata_path.open("r", encoding="utf-8") as f:
            metadata = json.load(f)

        if metadata.get("game_id") != game_id:
            raise ValueError(
                f"메타 game_id 불일치: expected={game_id}, actual={metadata.get('game_id')}"
            )

        self._cache[game_id] = metadata
        return metadata

    def find_clothes_atlas_path(
            self,
            game_id: str,
            gender: str,
            clothes_type: str,
    ) -> Path | None:
        """
        의상 옵션에 해당하는 atlas txt 경로를 찾는다.

        Args:
            game_id: 게임 식별자
            gender: 성별 옵션
            clothes_type: 의상 종류

        Returns:
            atlas txt 경로가 있으면 Path, 없으면 None
        """

        metadata = self.load_game_metadata(game_id)

        atlas_map = (
            metadata
            .get("categories", {})
            .get("clothes", {})
            .get("atlas", {})
        )

        atlas_info = (
            atlas_map
            .get(gender, {})
            .get(clothes_type)
        )

        if not atlas_info:
            return None

        atlas_path = atlas_info.get("atlas_path")

        if not atlas_path:
            return None

        # 상대 경로는 metadata 파일 기준이 아니라 프로젝트/게임 설정 기준으로 해석할 수 있게 문자열만 Path화한다.
        return Path(atlas_path)
