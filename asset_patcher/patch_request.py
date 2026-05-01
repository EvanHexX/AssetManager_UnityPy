# asset_patcher/models/patch_request.py
# 설명:
# React/Electron 쪽에서 전달되는 단일 패치 요청 구조를 정의한다.
# 의상 PNG 패치에서는 category=clothes, option1=gender, option2=clothes type 으로 사용한다.

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PatchRequest:
    """
    React/Electron에서 전달된 패치 요청을 표현한다.

    Args:
        game_id: 게임 식별자. 예: LongYinLiZhiZhuan
        category: 패치 분류. 예: clothes, font
        option1: 1차 옵션. clothes에서는 gender
        option2: 2차 옵션. clothes에서는 의상 종류
        texture_name: Texture2D 이름 또는 atlas page 이름. 예: skeleton_1.png
        path_id: Unity Texture2D PathID
        size: React 쪽에서 전달한 기준 크기 [width, height]
    """

    game_id: str
    category: str
    option1: str
    option2: str
    texture_name: str
    path_id: int
    size: tuple[int, int]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PatchRequest":
        """
        dict 데이터를 PatchRequest로 변환한다.

        Args:
            data: React/Electron에서 전달된 JSON dict

        Returns:
            PatchRequest 인스턴스

        Raises:
            ValueError: 필수 필드가 없거나 size 형식이 잘못된 경우
        """

        required = [
            "game_id",
            "category",
            "option1",
            "option2",
            "texture_name",
            "pathID",
            "size",
        ]

        # 필수 필드 누락 여부를 먼저 검사한다.
        missing = [key for key in required if key not in data]
        if missing:
            raise ValueError(f"PatchRequest 필수 필드 누락: {missing}")

        raw_size = data["size"]

        # size는 [width, height] 형태만 허용한다.
        if (
                not isinstance(raw_size, (list, tuple))
                or len(raw_size) != 2
        ):
            raise ValueError(f"size는 [width, height] 형태여야 합니다: {raw_size}")

        width = int(raw_size[0])
        height = int(raw_size[1])

        if width <= 0 or height <= 0:
            raise ValueError(f"size 값은 1 이상이어야 합니다: {raw_size}")

        return cls(
            game_id=str(data["game_id"]),
            category=str(data["category"]),
            option1=str(data["option1"]),
            option2=str(data["option2"]),
            texture_name=str(data["texture_name"]),
            path_id=int(data["pathID"]),
            size=(width, height),
        )
