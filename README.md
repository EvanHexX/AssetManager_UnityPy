# AssetManager_UnityPy

Unity 기반 게임의 `.assets / .resS / AssetBundle` 리소스를  
**안전하게 패치하기 위한 Python 기반 도구**

---

# 🎯 목적

- Unity Texture2D (특히 `.resS` 구조) 안전 교체
- Spine atlas 기반 이미지 교체 지원
- font / atlas / texture 통합 패치 시스템 구축
- Electron 앱과 연동 가능한 CLI/EXE 제공

---

# 🚨 핵심 특징

## 1. `.resS` 구조 안전 패치

Unity 대형 텍스처는 다음 구조를 사용:

```

sharedassets1.assets      → 메타데이터
sharedassets1.assets.resS → 실제 이미지 데이터

```

일반적인 툴(UABEA 등)은:

```

resS → assets 내부로 이동
→ 파일 크기 증가
→ 크래시 발생

```

❗ 본 프로젝트는 `.assets`를 변경하지 않고  
`.resS`만 직접 수정하여 안정성을 확보

---

## 2. PathID 기반 패치

Unity에서는 동일 이름 Texture가 여러 개 존재할 수 있음

```

skeleton_17 (남자)
skeleton_17 (여자)

```

👉 해결:

```

Texture 이름 ❌
PathID ✔

```

---

## 3. 모듈 기반 구조

```

texture_patch   → Texture2D 교체
atlas_patch     → atlas 텍스트 수정
font_patch      → 폰트 교체
bundle_patch    → AssetBundle 처리 (예정)

```

---

# 📂 프로젝트 구조

```
AssetManager_UnityPy/
├─ asset_patcher/
│  ├─ __init__.py
│  ├─ cli.py
│  ├─ plan_loader.py
│  ├─ core/
│  ├─ ├─ __init__.py
│  ├─ └─ backup.py
│  └─ modules/
│     ├─ __init__.py
│     ├─ texture_ress_patch.py
│     ├─ atlas_patch.py
│     ├─ font_patch.py
│     └─ bundle_patch.py
├─ schemas/
│  └─ patch_plan.schema.json
├─ examples/
│  └─ patch_plan.example.json
├─ tests/
├─ build/
├─ requirements.txt
└─ README.md

````

---

# 🚀 설치

```bash
pip install UnityPy pillow
````

---

# 🔧 기본 사용 (Texture 교체)

```bash
python patch_texture_ress.py \
  --assets "sharedassets1.assets" \
  --path-id 123456 \
  --png "skeleton_17.png" \
  --out "./output"
```

---

# ⚠️ 주의사항

## 1. 해상도 반드시 동일

```
원본: 1763 x 1050
→ 교체도 동일해야 함
```

❌ 변경 시:

* UV 깨짐
* 파츠 위치 오류

---

## 2. RGBA 유지

* PNG는 반드시 RGBA (알파 포함)
* 투명도 깨지면 캐릭터 손상

---

## 3. `.assets` 파일 직접 수정 금지

👉 반드시 `.resS`만 수정

---

# 🧠 내부 동작 원리

1. UnityPy로 Texture2D 메타데이터 읽기
2. `m_StreamData`에서:

   * offset
   * size
   * path (.resS)
     확인
3. `.resS` 파일 직접 seek → overwrite

---

# 📦 향후 기능

* [ ] atlas 자동 수정 (좌표 scaling)
* [ ] 고해상도 atlas 재구성
* [ ] font 자동 교체 (TMP 포함)
* [ ] AssetBundle 패치 지원
* [ ] GUI (Electron 연동)
* [ ] 패치 프로파일 관리
* [ ] 자동 백업 / 롤백 시스템

---

# 🔗 Electron 연동

CLI 기반 JSON 작업 처리 예정

```bash
AssetManager_UnityPy.exe --job job.json
```

---

# 🧪 테스트 상태

| 기능                | 상태     |
| ----------------- | ------ |
| Texture2D resS 패치 | ✅ 완료   |
| PathID 분기         | ✅ 완료   |
| atlas patch       | 🔄 진행중 |
| font patch        | ⏳ 예정   |
| EXE 빌드            | ⏳ 예정   |

---

# 💬 개발 방향

이 프로젝트는 단순 스크립트가 아니라:

```
Unity Asset Patch Framework
```

를 목표로 합니다.

---

# 🧠 핵심 철학

```
파일을 바꾸지 않는다
→ 메모리 구조를 이해한다
→ 필요한 부분만 정확히 수정한다
```

---

# 📌 타겟 게임

* LongYinLiZhiZhuan (용윤입지전)
* Unity 기반 게임 전반 확장 가능

---

# 🛠️ 라이선스

개인 사용 및 연구 목적

---

# 🙏 참고

* UnityPy
* UABEA
* AssetStudio

---
해당 README.md 파일은 llm을 통해 작성했습니다.

