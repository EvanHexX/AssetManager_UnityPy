# TODO: Texture2D 크기 변경 Patch

## 현재 상태

동일 크기 PNG는 `.resS` 직접 patch로 성공 가능하다.

현재 안정 흐름:

```text
React/Electron 요청
→ data.tsv 검증
→ atlas TextAsset 현재 size 확인
→ PNG size == 현재 atlas size
→ .resS 직접 patch
````

## 보류 중인 기능

PNG 크기가 원본 Texture2D 크기와 다를 때:

```text
Texture2D width/height 변경
m_StreamData size 변경
image data 재삽입
.assets 저장
.resS 또는 .assets 내부 저장 위치 결정
container/pathID/name 유지 검증
```

## 위험 요소

* UnityPy `env.file.save()`가 container/path 구조를 바꿀 수 있음
* Texture2D `read()`는 `check_read=False` 필요
* 기존 `.resS` stream size보다 큰 PNG는 단순 overwrite 불가
* Texture2D stream offset/size 재배치 필요 가능성 있음
* AssetStudio/UABEA 방식처럼 `.assets` 크기 증가 시 게임 크래시 가능

## 구현 전 필수 검증

1. `obj.read(check_read=False)`로 Texture2D 읽기
2. `data.image = new_image`
3. `data.save()`
4. `env.file.save()` 결과 저장
5. 저장 전후 비교:

   * PathID 동일
   * Texture name 동일
   * container snapshot 동일
   * Texture2D type 동일
   * atlas TextAsset PathID 동일
6. 게임 실행 테스트

## 권장 구현 방향

`texture_resize_patch.py`를 별도 experimental 모듈로 만든다.

```text
asset_patcher/modules/texture_resize_patch.py
```

초기에는 원본 덮어쓰기 금지.

```text
outputDir에만 저장
실제 게임 폴더 교체는 수동 테스트
```

## 성공 조건

* 업스케일 PNG가 정상 표시됨
* 게임 시작 크래시 없음
* Spine 애니메이션 정상
* atlas bounds/offsets 정상
* 같은 의상 여러 page 연속 patch 가능
* 반복 patch 시 atlas 배율 중복 적용 없음

````

이제 React/Electron 연결과 빌드 쪽은 다음 순서가 좋습니다.

```text
1. patch_plan JSON 계약 고정
2. Python CLI 입출력 안정화
3. Electron에서 child_process로 exe 호출
4. reports JSON 읽어서 UI 표시
5. Nuitka 빌드
````

다음으로 만들 파일:

```text
docs/API_contract.md
scripts/build_nuitka.ps1
```

그리고 CLI는 지금처럼 유지하되 React 쪽에서는 항상 이런 방식으로 호출하면 됩니다.

```powershell
AssetManager_UnityPy.exe --plan patch_plan.json --report patch_report.json
```
