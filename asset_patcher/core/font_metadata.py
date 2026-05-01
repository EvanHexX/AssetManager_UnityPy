# asset_patcher/core/font_metadata.py
# 설명:
# fonts_data.tsv를 기준으로 Font 패치 대상을 검증한다.
# Arial도 포함하며, 제외가 필요하면 TSV에서 해당 행을 삭제한다.

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FontMetadata:
    name: str
    description: str
    type_name: str
    path_id: int
    source: str


class FontMetadataStore:
    """
    fonts_data.tsv 로더.
    """

    def __init__(self, tsv_path: str | Path) -> None:
        self.tsv_path = Path(tsv_path)
        self._items: list[FontMetadata] = []
        self._loaded = False

    def load(self) -> None:
        """
        fonts_data.tsv를 로드한다.
        """

        if self._loaded:
            return

        if not self.tsv_path.exists():
            raise FileNotFoundError(f"Font metadata TSV가 없습니다: {self.tsv_path}")

        with self.tsv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")

            required_columns = {
                "Name",
                "Description",
                "Type",
                "PathID",
                "Source",
            }

            missing_columns = required_columns - set(reader.fieldnames or [])

            if missing_columns:
                raise ValueError(
                    f"Font metadata TSV 필수 컬럼 누락: {sorted(missing_columns)}"
                )

            for row in reader:
                name = row["Name"].strip()

                # ✅ 빈 이름 행은 잘못된 데이터로 보고 중단한다.
                if not name:
                    raise ValueError(f"Font metadata에 빈 Name 행이 있습니다: {row}")

                self._items.append(
                    FontMetadata(
                        name=name,
                        description=row["Description"].strip(),
                        type_name=row["Type"].strip(),
                        path_id=int(row["PathID"]),
                        source=row["Source"].strip(),
                    )
                )

        self._validate_unique_path_ids()
        self._loaded = True

    def find_by_name(self, name: str) -> FontMetadata:
        """
        Font 이름 기준으로 metadata를 찾는다.

        주의:
            같은 이름이 여러 개면 안전하지 않으므로 실패 처리한다.
            이 경우 CLI plan에서 path_id를 직접 사용해야 한다.
        """

        self.load()

        normalized_name = name.strip()

        matches = [
            item
            for item in self._items
            if item.name == normalized_name
        ]

        if len(matches) != 1:
            raise ValueError(
                f"Font metadata name 매칭 실패: "
                f"name={normalized_name}, matches={len(matches)}. "
                "중복 이름 가능성이 있으므로 path_id 기준 사용을 권장합니다."
            )

        return matches[0]

    def find_by_path_id(self, path_id: int) -> FontMetadata:
        """
        Font PathID 기준으로 metadata를 찾는다.
        """

        self.load()

        parsed_path_id = int(path_id)

        matches = [
            item
            for item in self._items
            if item.path_id == parsed_path_id
        ]

        if len(matches) != 1:
            raise ValueError(
                f"Font metadata PathID 매칭 실패: "
                f"pathID={parsed_path_id}, matches={len(matches)}"
            )

        return matches[0]

    def list_all(self) -> list[FontMetadata]:
        """
        등록된 모든 Font metadata를 반환한다.
        """

        self.load()
        return list(self._items)

    def _validate_unique_path_ids(self) -> None:
        """
        PathID 중복 여부를 검사한다.
        """

        seen: dict[int, str] = {}

        for item in self._items:
            if item.path_id in seen:
                raise ValueError(
                    "Font metadata PathID 중복: "
                    f"pathID={item.path_id}, first={seen[item.path_id]}, second={item.name}"
                )

            seen[item.path_id] = item.name