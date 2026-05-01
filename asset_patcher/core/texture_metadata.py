# asset_patcher/core/texture_metadata.py
# 설명:
# data.tsv를 기준으로 의상 Texture2D 패치 요청을 검증한다.
# React/Electron 요청의 category=clothes는 TSV의 category=Outfit으로 매핑한다.

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TextureMetadata:
    category: str
    gender: str
    clothes_type: str
    texture_name: str
    path_id: int
    size: tuple[int, int]
    atlas_name: str | None
    atlas_path_id: int | None
    texture_format: str

    @property
    def atlas_page_name(self) -> str:
        """
        atlas txt에서 사용하는 page 이름을 반환한다.
        TSV texture_name은 skeleton_2 형태이고, atlas page는 skeleton_2.png 형태다.
        """

        if self.texture_name.lower().endswith(".png"):
            return self.texture_name

        return f"{self.texture_name}.png"


class TextureMetadataStore:
    """
    Texture metadata TSV 로더.
    """

    def __init__(self, tsv_path: str | Path) -> None:
        self.tsv_path = Path(tsv_path)
        self._items: list[TextureMetadata] = []
        self._loaded = False

    def load(self) -> None:
        """
        data.tsv를 로드한다.
        """

        if self._loaded:
            return

        if not self.tsv_path.exists():
            raise FileNotFoundError(f"Texture metadata TSV가 없습니다: {self.tsv_path}")

        with self.tsv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")

            required_columns = {
                "category",
                "gender",
                "type",
                "texture_name",
                "pathID",
                "size",
                "atlas_name",
                "atlas_pathID",
                "format",
            }

            missing_columns = required_columns - set(reader.fieldnames or [])

            if missing_columns:
                raise ValueError(
                    f"Texture metadata TSV 필수 컬럼 누락: {sorted(missing_columns)}"
                )

            for row in reader:
                width, height = self._parse_size(row["size"])

                atlas_name = self._none_if_empty_or_none(row["atlas_name"])
                atlas_path_id = self._parse_optional_int(row["atlas_pathID"])

                self._items.append(
                    TextureMetadata(
                        category=row["category"].strip(),
                        gender=row["gender"].strip(),
                        clothes_type=row["type"].strip(),
                        texture_name=self._normalize_texture_name(row["texture_name"]),
                        path_id=int(row["pathID"]),
                        size=(width, height),
                        atlas_name=atlas_name,
                        atlas_path_id=atlas_path_id,
                        texture_format=row["format"].strip(),
                    )
                )

        self._loaded = True

    def find_exact(
        self,
        category: str,
        gender: str,
        clothes_type: str,
        texture_name: str,
        path_id: int,
        size: tuple[int, int],
    ) -> TextureMetadata:
        """
        React/Electron 요청값과 정확히 일치하는 Texture metadata를 찾는다.
        """

        self.load()

        normalized_category = self._normalize_category(category)
        normalized_texture_name = self._normalize_texture_name(texture_name)

        matches = [
            item
            for item in self._items
            if item.category == normalized_category
            and item.gender == gender.strip()
            and item.clothes_type == clothes_type.strip()
            and item.texture_name == normalized_texture_name
            and item.path_id == int(path_id)
            and item.size == tuple(size)
        ]

        if len(matches) != 1:
            raise ValueError(
                "Texture metadata 정확 매칭 실패: "
                f"category={category}->{normalized_category}, "
                f"gender={gender}, type={clothes_type}, "
                f"texture={texture_name}->{normalized_texture_name}, "
                f"pathID={path_id}, size={size}, matches={len(matches)}"
            )

        metadata = matches[0]

        if metadata.texture_format != "RGBA32":
            raise ValueError(
                f"현재는 RGBA32만 지원합니다: "
                f"texture={metadata.texture_name}, format={metadata.texture_format}"
            )

        return metadata

    @staticmethod
    def _normalize_category(value: str) -> str:
        """
        React category와 TSV category를 매핑한다.
        """

        aliases = {
            "clothes": "Outfit",
            "outfit": "Outfit",
            "Outfit": "Outfit",
        }

        return aliases.get(value.strip(), value.strip())

    @staticmethod
    def _normalize_texture_name(value: str) -> str:
        """
        texture_name을 TSV 기준으로 정규화한다.
        skeleton_2.png → skeleton_2
        """

        value = value.strip()

        if value.lower().endswith(".png"):
            return value[:-4]

        return value

    @staticmethod
    def _parse_size(value: str) -> tuple[int, int]:
        """
        '1024,512' 형태의 size 값을 파싱한다.
        """

        parts = value.strip().split(",")

        if len(parts) != 2:
            raise ValueError(f"잘못된 size 형식: {value}")

        return int(parts[0]), int(parts[1])

    @staticmethod
    def _none_if_empty_or_none(value: str) -> str | None:
        """
        None 문자열 또는 빈 문자열을 None으로 변환한다.
        """

        value = value.strip()

        if not value or value.lower() == "none":
            return None

        return value

    @staticmethod
    def _parse_optional_int(value: str) -> int | None:
        """
        atlas_pathID 값을 파싱한다.
        -1 또는 빈 값은 None으로 처리한다.
        """

        value = value.strip()

        if not value:
            return None

        parsed = int(value)

        if parsed < 0:
            return None

        return parsed