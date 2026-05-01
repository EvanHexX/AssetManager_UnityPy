## examples

```text
patch_plan.json
 ├─ planName      전체 패치 계획 이름
 ├─ game          대상 게임 정보
 ├─ options       실행 옵션
 └─ tasks         실제 패치 작업 목록
```

## task type 후보

```text
texture_ress_patch   .assets + .resS 기반 Texture2D 교체
atlas_text_patch      skeleton.atlas 텍스트 수정/좌표 스케일링
font_patch            Font/TMP Font 교체
file_copy_patch       단순 파일 교체
assetbundle_patch     AssetBundle 대상 교체
```

## 핵심 원칙

`texture_ress_patch`는 반드시 `pathId` 중심으로 갑니다.

```json
"target": {
  "pathId": 123456
}
```
## 실행
```powershell
python -m asset_patcher.cli --plan ".\examples\patch_plan.example.json"
```

`textureName`은 검증용입니다.
동명이 Texture2D가 있을 수 있으니 실제 타깃 식별자는 **PathID**입니다.

### Batch Patch
```PowerShell
python -m asset_patcher.cli `
  --plan .\examples\patch_plan.clothes.example.json `
  --report .\reports\patch_report.json
```

### Font Patch
```Python
from asset_patcher.core.font_metadata import FontMetadataStore
from asset_patcher.core.original_store import OriginalStore
from asset_patcher.modules.font_patch import FontPatcher

patcher = FontPatcher(
    font_metadata_store=FontMetadataStore("metadata/fonts_data.tsv"),
    original_store=OriginalStore("originals"),
)

# 첫 실행 시 원본 폰트 전체 추출
patcher.extract_originals(
    game_id="LongYinLiZhiZhuan",
    assets_file="D:/Games/.../LongYinLiZhiZhuan_Data/resources.assets",
)

# 특정 폰트 교체
result = patcher.patch_by_name(
    game_id="LongYinLiZhiZhuan",
    font_name="Arial",
    assets_file="D:/Games/.../LongYinLiZhiZhuan_Data/resources.assets",
    replacement_font_file="D:/Mods/fonts/MyFont.ttf",
    dry_run=False,
)
```