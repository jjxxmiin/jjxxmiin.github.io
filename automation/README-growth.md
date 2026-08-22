# OPSOAI 유입 확대 도구 모음

GA4 실측(2026-08-22, 최근 90일) 기준 문제는 하나다. **하루 검색 세션 4.4**,
612편 중 521편이 90일간 검색 유입 0. 세션당 PV나 광고 배치가 아니라
**검색 유입 자체**가 병목이므로, 여기 도구들은 전부 그 한 항을 겨냥한다.

## 도구

| 스크립트 | 하는 일 | 언제 |
| --- | --- | --- |
| `apply_tags.py` | 통제 어휘로 태그 부여 (관련글 추천 복구) | 어휘 변경 시 |
| `tag_taxonomy.py` | 태그 어휘 정의. 봇도 이걸 공유한다 | 어휘 편집 |
| `normalize_categories.py` | 카테고리 정규화 | 카테고리 추가 시 |
| `clean_image_alt.py` | arXiv 캡션에서 온 LaTeX alt 정리 | 논문 글 발행 후 |
| `protect_liquid.py` | 코드 예제의 `{{ }}` 를 Liquid에서 보호 | Actions와 템플릿 코드 포함 글 발행 후 |
| `harvest_keywords.py` | 구글과 네이버 자동완성에서 실검색어 수집 | 분기 1회 |
| `KEYWORDS.md` | 수집 결과를 실행 순서로 정리한 키워드 뱅크 | 글 쓰기 전 |
| `search_console.py` | 노출, CTR, 순위로 되살릴 글 찾기 | 주 1회 |

## 네이버 서치어드바이저 — 최초 1회 설정

소유확인은 이미 되어 있다(`_config.yml`의 `webmaster_verifications.naver`,
홈 `<meta name="naver-site-verification">`으로 렌더 확인함). 남은 건 제출뿐이다.

[searchadvisor.naver.com](https://searchadvisor.naver.com) → 웹마스터 도구 →
`www.opsoai.com` 선택 후:

1. **요청 → 사이트맵 제출**: `https://www.opsoai.com/sitemap.xml`
   (749개 URL, 107KB. 네이버 상한은 5만 URL / 10MB이므로 여유 있음)
2. **요청 → RSS 제출**: `https://www.opsoai.com/feed.xml`
   피드 항목 수를 테마 기본 5개에서 **20개로 올려 뒀다**(`assets/feed.xml`).
   하루 2편 발행 체제에서 5개면 수집 주기가 조금만 밀려도 글이 통째로 누락된다.
3. **검증 → robots.txt**: `Yeti` 허용은 이미 들어가 있다. 확인만.
4. **웹 페이지 수집**: 주요 글 몇 개를 수동 수집 요청해 색인 속도를 당긴다.

현재 네이버 유입은 90일 48세션(naver 36 + m.search.naver.com 12)에 불과하다.
이 기준선과 비교해 효과를 측정할 것.

## 네이버 블로그는 운영하지 않는다

검토했지만 하지 않기로 했다(2026-08-23 결정). 네이버 블로그는 도메인 권위가
높아 같은 글을 올리면 구글에서 네이버판이 원문을 이기고, 그러면 애드센스가
붙은 본진 대신 단가 낮은 애드포스트로 트래픽이 샌다. 요약본만 올리는 절충안도
있으나 발행이 전부 수동(네이버는 공개 글쓰기 API가 없다)이라 품이 든다.

**검색엔진 연결만 한다.** 원문을 opsoai.com 한 곳에 모으고 각 검색엔진이
직접 긁어가게 하는 편이, 채널을 늘리는 것보다 지금 단계에서 회수가 크다.

## Search Console — 최초 1회 설정

`search_console.py`가 돌려면 두 가지가 필요하다.

```bash
gcloud services enable searchconsole.googleapis.com --project=teachingflow
```

그리고 [search.google.com/search-console](https://search.google.com/search-console)
→ 설정 → 사용자 및 권한 → 사용자 추가 →
`agent-231@teachingflow.iam.gserviceaccount.com` (전체 권한).

```bash
python automation/search_console.py --days 90 --report ctr       # 제목만 고쳐 되살릴 글
python automation/search_console.py --days 90 --report striking  # 11~30위 = 1페이지 문턱
```

GA4에는 노출(impressions)이 없다. 521편이 "검색 수요가 없어서" 0인지
"노출은 되는데 안 눌려서" 0인지는 Search Console로만 구분된다. 이 구분이
새 글을 쓸지 기존 글을 고칠지를 가른다.

## GA4

키는 `teachingflow-9e21043e4c25.json`(속성 `463694693`). `.env`가 가리키는
`GA4_CREDENTIALS_JSON.json`은 서비스 계정이 삭제돼 죽어 있으니 쓰지 말 것.
두 파일 다 `.gitignore` 처리돼 있다 — **공개 저장소이므로 절대 커밋 금지.**

측정할 때 주의: 90일 세션의 국가 분포가 싱가포르 899와 한국 879와 미국 617와 중국 417이고, Direct 2,151 중 한국은 206뿐이다. 나머지 약 1,945는 데이터센터
봇으로 보인다. **국가 필터 없이 본 겉숫자는 실제 독자의 두세 배로 부풀어 있다.**
