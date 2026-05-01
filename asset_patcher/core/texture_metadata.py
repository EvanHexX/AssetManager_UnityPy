# asset_patcher/core/texture_metadata.py
# 설명:
# data.tsv를 기준으로 의상 Texture2D 패치 요청을 검증한다.

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
        return f"{self.texture_name}.png"


class TextureMetadataStore:
    def __init__(self, tsv_path: str | Path) -> None:
        self.tsv_path = Path(tsv_path)
        self._items: list[TextureMetadata] = []
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return

        if not self.tsv_path.exists():
            raise FileNotFoundError(f"Texture metadata TSV가 없습니다: {self.tsv_path}")

        with self.tsv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")

            for row in reader:
                width, height = self._parse_size(row["size"])
                atlas_name = row["atlas_name"]
                atlas_path_id = int(row["atlas_pathID"])

                self._items.append(
                    TextureMetadata(
                        category=row["category"],
                        gender=row["gender"],
                        clothes_type=row["type"],
                        texture_name=row["texture_name"],
                        path_id=int(row["pathID"]),
                        size=(width, height),
                        atlas_name=None if atlas_name == "None" else atlas_name,
                        atlas_path_id=None if atlas_path_id < 0 else atlas_path_id,
                        texture_format=row["format"],
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
        self.load()

        matches = [
            item
            for item in self._items
            if item.category == category
               and item.gender == gender
               and item.clothes_type == clothes_type
               and item.texture_name == texture_name
               and item.path_id == path_id
               and item.size == size
        ]

        if len(matches) != 1:
            raise ValueError(
                "Texture metadata 정확 매칭 실패: "
                f"category={category}, gender={gender}, type={clothes_type}, "
                f"texture={texture_name}, pathID={path_id}, size={size}, "
                f"matches={len(matches)}"
            )

        metadata = matches[0]

        if metadata.texture_format != "RGBA32":
            raise ValueError(
                f"현재는 RGBA32만 지원합니다: "
                f"texture={metadata.texture_name}, format={metadata.texture_format}"
            )

        return metadata

    @staticmethod
    def _parse_size(value: str) -> tuple[int, int]:
        parts = value.split(",")

        if len(parts) != 2:
            raise ValueError(f"잘못된 size 형식: {value}")

        return int(parts[0]), int(parts[1])
