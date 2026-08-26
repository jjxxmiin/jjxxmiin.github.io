"""OPSOAI 태그 통제 어휘(controlled vocabulary).

관련글 추천은 태그 교집합으로 동작하므로, 태그는 코퍼스를 '분할'해야 한다.
전체 글에 달리는 태그(예: 'AI')는 모든 글을 모든 글과 엮어 추천을 무의미하게
만들기 때문에 어휘에서 제외했다. 각 태그는 변별력을 갖는 주제 단위로만 둔다.

각 항목은 (태그명, [정규식...], 옵션) 형태다. 옵션 키:

    title_only  제목에서만 매칭한다. '논문리뷰'처럼 본문 어디서나 튀어나오는
                단어로 판정하면 오탐이 폭발하는 내용 유형 태그에 쓴다.
    min         이 점수 미만이면 태그를 붙이지 않는다. 설치 안내에 한 번 스쳐
                지나가는 기업명(Apple, Nvidia 등)을 걸러내는 용도.
                제목 매칭 1회 = TITLE_WEIGHT점, 본문은 패턴당 최대 3점이므로
                min=4는 "제목에 있거나, 본문에서 뚜렷하게 반복될 것"을 뜻한다.
"""

# 제목에서 매칭됐을 때의 가중치. 제목은 글의 주제를 본문보다 정확히 대변한다.
TITLE_WEIGHT = 6

# 한 글에 붙일 최대/최소 태그 수. 두 개 미만이면 주제 연결이 지나치게 약하고,
# 여섯 개 이상이면 관련글 후보가 오히려 넓어지므로 핵심 태그만 남긴다.
MAX_TAGS = 5
MIN_TAGS = 2

# 코퍼스의 이 비율을 넘게 매칭되는 태그는 변별력이 없다고 보고 후순위로 강등한다.
GENERIC_RATIO = 0.35

# 현재 코퍼스 전수 분석에서 실제로 GENERIC_RATIO를 넘긴 태그들. 자동 발행 봇은 코퍼스
# 전체 통계를 낼 수 없으므로 이 목록을 그대로 써서 기존 글과 같은 기준을 적용한다.
# 어휘를 크게 바꾸면 apply_tags.py를 드라이런해 이 값을 갱신할 것.
DEMOTED = {"AI에이전트"}

TAXONOMY = [
    # ---------- 모델과 기업 ----------
    # 스쳐 지나가는 언급이 잦은 대형 벤더는 min을 걸어 주제일 때만 붙인다.
    ("OpenAI",        [r"openai", r"오픈에이아이"], {"min": 4}),
    ("ChatGPT",       [r"chatgpt", r"챗ai?gpt", r"챗지피티"], {}),
    ("GPT",           [r"\bgpt[-‑ ]?\d", r"gpt-?4o", r"지피티"], {"min": 4}),
    ("Anthropic",     [r"anthropic", r"앤트로픽"], {"min": 4}),
    ("Claude",        [r"claude", r"클로드"], {"min": 4}),
    ("ClaudeCode",    [r"claude[ -]?code", r"클로드[ -]?코드"], {}),
    # '애플리케이션'이 '애플'로 잡히는 사고를 막는다. 코퍼스에서 182회 오탐이었다.
    ("Apple",         [r"\bapple\b", r"애플(?!리케이션|리케)", r"\bmlx\b"], {"min": 6}),
    ("Google",        [r"\bgoogle\b", r"구글", r"deepmind", r"딥마인드"], {"min": 4}),
    ("Gemini",        [r"gemini", r"제미나이", r"제미니"], {}),
    ("Meta",          [r"\bmeta\s+ai\b", r"메타 ?ai", r"\bfair\b 연구"], {"min": 4}),
    # 'Ollama'와 'llama.cpp'는 Meta의 Llama 모델이 아니다.
    ("Llama",         [r"(?<!o)llama(?!\.cpp)", r"라마 ?\d"], {"min": 4}),
    ("Nvidia",        [r"nvidia", r"엔비디아"], {"min": 4}),
    ("DeepSeek",      [r"deepseek", r"딥시크"], {}),
    ("Qwen",          [r"qwen", r"큐원", r"알리바바", r"alibaba"], {}),
    ("Mistral",       [r"mistral", r"미스트랄"], {}),
    ("HuggingFace",   [r"hugging ?face", r"허깅페이스"], {"min": 4}),
    ("Microsoft",     [r"microsoft", r"마이크로소프트", r"\bcopilot\b", r"코파일럿"], {"min": 4}),
    ("xAI",           [r"\bxai\b", r"\bgrok\b", r"그록"], {}),

    # ---------- 기술 영역 ----------
    ("LLM",           [r"\bllm\b", r"대규모 ?언어 ?모델", r"거대 ?언어 ?모델",
                       r"\barchon\b"], {}),
    ("멀티모달",       [r"멀티모달", r"multimodal", r"\bvlm\b", r"비전 ?언어"], {}),
    ("컴퓨터비전",     [r"컴퓨터 ?비전", r"computer ?vision", r"객체 ?(?:탐지|인식|추적)",
                       r"object ?(?:detection|tracking)", r"multi[- ]?object ?tracking",
                       r"이미지 ?분류", r"세그멘테이션", r"segmentation", r"bounding ?box",
                       r"feature ?pyramid", r"\bfpn\b", r"\bcornernet\b", r"\bssd\b",
                       r"deep ?sort", r"efficientdet", r"efficientnet",
                       r"crowd ?count", r"density ?map", r"face ?recognition", r"\bfacenet\b"], {}),
    ("이미지생성",     [r"이미지 ?생성", r"text[- ]?to[- ]?image", r"image[- ]?to[- ]?image",
                       r"stable ?diffusion", r"\bcyclegan\b", r"미드저니", r"midjourney",
                       r"\bdall[- ]?e\b", r"이미지 ?편집"], {}),
    ("영상생성",       [r"비디오 ?생성", r"영상 ?생성", r"video[- ]?generation",
                       r"video[- ]?audio[- ]?generation", r"text[- ]?to[- ]?video",
                       r"(?<![a-z0-9])lol(?![a-z0-9]).*(?:sink[- ]?collapse|rope ?jitter)", r"\bmova\b",
                       r"\bsora\b", r"동영상 ?생성", r"비디오 ?모델"], {}),
    ("영상이해",       [r"비디오 ?이해", r"영상 ?이해", r"video ?understanding",
                       r"video[- ]?(?:auto[- ]?)?reasoning", r"visual[- ]?reasoning",
                       r"video ?llm", r"videoauto[- ]?r1", r"비디오 ?추론", r"영상 ?추론", r"internvideo",
                       r"capimagine", r"proact[- ]?vl"], {}),
    ("문서AI",         [r"\bocr\b", r"문서 ?이해", r"document ?intelligence",
                       r"document ?understanding", r"문서 ?파싱", r"레이아웃 ?인식"], {}),
    ("음성AI",         [r"음성 ?인식", r"\btts\b", r"\bstt\b", r"음성 ?합성",
                       r"whisper", r"오디오 ?생성", r"보이스 ?클론"], {}),
    ("3D생성",         [r"포인트 ?클라우드", r"point ?cloud", r"\bnerf\b",
                       r"가우시안 ?스플래팅", r"gaussian ?splatting", r"메시 ?생성",
                       r"3d ?(생성|재구성|에셋)"], {}),
    ("로보틱스",       [r"로보틱스", r"로봇", r"\brobot", r"\bvla\b", r"임바디드",
                       r"embodied", r"매니퓰레이션"], {}),
    ("강화학습",       [r"강화 ?학습", r"reinforcement ?learning", r"\brlhf\b",
                       r"\bgrpo\b", r"\bppo\b", r"보상 ?모델"], {}),
    ("월드모델",       [r"월드 ?모델", r"world ?model", r"세계 ?모델"], {}),

    # ---------- 개념과 기법 ----------
    ("RAG",           [r"\brag\b", r"검색 ?증강", r"retrieval[- ]?augmented"], {}),
    ("벡터DB",         [r"벡터 ?db", r"벡터 ?데이터베이스", r"vector ?(db|database|store)",
                       r"임베딩 ?검색", r"\bfaiss\b", r"\bchroma\b", r"\bqdrant\b"], {}),
    ("파인튜닝",       [r"파인 ?튜닝", r"fine[- ]?tun", r"\blora\b", r"\bqlora\b",
                       r"\bpeft\b", r"미세 ?조정", r"post[- ]?training"], {}),
    ("프롬프트엔지니어링", [r"프롬프트 ?엔지니어링", r"prompt ?engineering", r"프롬프트 ?설계",
                       r"시스템 ?프롬프트", r"컨텍스트 ?엔지니어링"], {}),
    ("트랜스포머",     [r"트랜스포머", r"transformer", r"어텐션", r"self[- ]?attention",
                       r"\bmoe\b", r"mixture ?of ?experts"], {}),
    ("디퓨전모델",     [r"디퓨전", r"diffusion", r"확산 ?모델", r"플로우 ?매칭"], {}),
    ("경량화",         [r"양자화", r"quantiz", r"\bgguf\b", r"지식 ?증류", r"distill",
                       r"프루닝", r"pruning", r"경량화", r"소형 ?모델", r"\bslm\b"], {}),
    ("온디바이스AI",   [r"온[- ]?디바이스", r"on[- ]?device", r"엣지 ?ai", r"edge ?ai",
                       r"로컬 ?llm", r"로컬 ?구동", r"\bollama\b", r"llama\.cpp",
                       r"\bopenvino\b", r"\bncs ?2\b", r"coral ?usb", r"raspberry ?pi"], {}),
    ("컨텍스트윈도우", [r"컨텍스트 ?(창|윈도우|길이)", r"context ?(window|length)",
                       r"롱 ?컨텍스트", r"long ?context", r"토큰 ?한계"], {}),
    ("AI메모리",       [r"ai ?(?:장기 ?)?기억", r"에이전트 ?메모리", r"장기 ?기억",
                       r"long[- ]?term ?memory", r"memory ?(?:system|architecture)",
                       r"\bmemoria\b"], {}),

    # ---------- 에이전트 ----------
    ("AI에이전트",     [r"ai ?에이전트", r"에이전트", r"\bagent\b", r"agentic"], {}),
    ("멀티에이전트",   [r"멀티 ?에이전트", r"multi[- ]?agent", r"다중 ?에이전트",
                       r"에이전트 ?오케스트레이션"], {}),
    ("MCP",           [r"\bmcp\b", r"model ?context ?protocol"], {}),
    ("AI코딩",         [r"ai ?코딩", r"코딩 ?에이전트", r"코드 ?생성", r"code ?generation",
                       r"\bcursor\b", r"\bcodex\b", r"\bcline\b", r"바이브 ?코딩",
                       r"vibe ?coding"], {}),
    ("업무자동화",     [r"업무 ?자동화", r"워크플로우 ?자동화", r"workflow ?automation",
                       r"\bn8n\b", r"자동화 ?파이프라인", r"뉴스 ?파이프라인",
                       r"trend ?pipeline", r"\btrendradar\b", r"\brpa\b"], {}),

    # ---------- 개발과 인프라 ----------
    ("오픈소스",       [r"오픈 ?소스", r"open ?source", r"mit ?라이선스",
                       r"apache ?2", r"자체 ?호스팅", r"self[- ]?host"], {}),
    ("파이썬",         [r"파이썬", r"\bpython\b", r"\bpytorch\b", r"파이토치",
                       r"\btensorflow\b", r"\bkeras\b", r"\bpep ?8\b"], {"min": 4}),
    ("MLOps",         [r"\bmlops\b", r"모델 ?배포", r"model ?serving", r"추론 ?서버",
                       r"\bvllm\b", r"triton", r"모델 ?서빙"], {}),
    ("인프라",         [r"쿠버네티스", r"kubernetes", r"도커", r"docker", r"데이터 ?센터",
                       r"data ?center", r"클라우드 ?인프라", r"(?<![a-z0-9])ebpf(?![a-z0-9])", r"\bredis\b",
                       r"\bkafka\b", r"\bredpanda\b", r"\bdragonfly\b"], {"min": 4}),
    ("데이터분석",     [r"\bxgboost\b", r"\blightgbm\b", r"\bkaggle\b", r"주성분 ?분석",
                       r"선형 ?판별", r"\bpca\b", r"\blda\b", r"통계 ?분석"], {}),
    ("웹개발",         [r"\bdjango\b", r"\bredux\b", r"\bzustand\b", r"백엔드",
                       r"backend", r"headless ?browser", r"헤드리스 ?브라우저",
                       r"node\.js", r"웹 ?프레임워크"], {}),
    ("API",           [r"api ?(공개|요금|가격|호출|키)", r"rest ?api", r"\bsdk\b"], {"min": 4}),
    ("반도체",         [r"반도체", r"\bhbm\b", r"\btpu\b", r"\bnpu\b", r"칩셋",
                       r"블랙웰", r"blackwell", r"\bcuda\b"], {}),

    # ---------- 보안, 정책, 안전 ----------
    ("AI보안",         [r"ai ?보안", r"프롬프트 ?인젝션", r"prompt ?injection",
                       r"탈옥", r"jailbreak", r"적대적 ?(?:공격|예제|교란)",
                       r"adversarial ?(?:attack|example|perturbation)",
                       r"취약점", r"사이버 ?보안", r"레드 ?팀", r"\bmagika\b",
                       r"\blibmagic\b", r"파일 ?유형 ?검증"], {}),
    ("AI정책",         [r"ai ?규제", r"ai ?정책", r"\bai act\b", r"거버넌스",
                       r"저작권", r"규제 ?당국"], {}),
    # bare 'alignment'는 컴퓨터비전 글의 Face Alignment(얼굴 정렬)에 걸린다.
    ("AI안전",         [r"ai ?안전", r"안전성 ?평가", r"정렬 ?(문제|위험|불일치)",
                       r"ai ?alignment", r"모델 ?정렬", r"ai ?윤리",
                       r"위험 ?평가", r"레드 ?티밍"], {"min": 4}),
    # 환각은 LLM 글마다 '한계' 항목으로 한 줄씩 나온다. 주제일 때만 붙도록 min을 높인다.
    ("환각문제",       [r"환각", r"hallucination", r"사실성 ?검증"], {"min": 6}),

    # ---------- 산업과 비즈니스 ----------
    ("AI투자",         [r"투자 ?유치", r"기업 ?가치", r"밸류에이션", r"\bipo\b",
                       r"펀딩", r"억 ?달러 ?투자"], {}),
    ("AI서비스",       [r"정식 ?출시", r"베타 ?서비스", r"신규 ?기능", r"요금제"], {}),

    # ---------- 내용 유형: 제목으로만 판정한다 ----------
    # 본문 스캔하면 '논문'은 495회, '[paper](' 링크는 586회 잡혀 전 코퍼스가 오염된다.
    ("논문리뷰",       [r"논문", r"\barxiv\b", r"톺아보기", r"paper ?review"],
                      {"title_only": True}),
    ("아키텍처분석",   [r"아키텍처", r"architecture", r"딥 ?다이브", r"deep ?dive",
                       r"해부", r"심층 ?분석", r"내부 ?구조", r"동작 ?원리", r"뜯어보기"],
                      {"title_only": True}),
    ("튜토리얼",       [r"사용법", r"설치 ?방법", r"시작하기", r"getting ?started",
                       r"따라 ?하기", r"실습", r"가이드", r"만들기", r"구축하기",
                       r"하는 ?법", r"세팅", r"체크리스트", r"점검 ?순서", r"설정 ?순서",
                       r"확인 ?순서", r"연결 ?순서", r"튜닝", r"선택 ?기준",
                       r"무엇부터"], {"title_only": True}),
    ("벤치마크",       [r"벤치마크", r"benchmark", r"리더보드", r"leaderboard",
                       r"성능 ?비교", r"비교 ?분석"], {"title_only": True}),
    ("AI트렌드",       [r"트렌드", r"전망", r"동향", r"패러다임", r"업계 ?분석",
                       r"시대", r"바뀌", r"판도"], {"title_only": True}),

    # ---------- 레거시 시리즈 ----------
    # 구조체(370회), 포인터(284회)는 DarkNet 코드 해설 전반에 깔려 있어 변별력이 없다.
    ("DarkNet",       [r"darknet", r"다크넷"], {}),
    ("YOLO",          [r"\byolo", r"욜로"], {}),
    ("C언어",          [r"c ?언어", r"\bmalloc\b", r"\bfree\(\)", r"\bstruct\b"], {"min": 4}),
]

# 본문 매칭으로 최소 태그 수를 못 채웠을 때 카테고리로 보전한다.
CATEGORY_FALLBACK = {
    "paper":         ["논문리뷰"],
    "basics":        ["튜토리얼", "AI트렌드"],
    "darknet":       ["DarkNet", "컴퓨터비전", "C언어"],
    "opensource":    ["오픈소스"],
    "edge":          ["온디바이스AI"],
    "reinforcement": ["강화학습"],
    "python":        ["파이썬"],
    "mlops":         ["MLOps"],
    "concept":       ["AI트렌드"],
    "review":        ["아키텍처분석"],
    "tech":          ["AI트렌드"],
    "ai":            ["AI트렌드"],
}

# 새 자동 글이 아직 어휘에 없는 주제를 다뤄도 관련글 그래프에서 고립되지 않게 한다.
# 구체 태그가 생기면 점수 정렬에서 이 두 범용 태그보다 앞선다.
DEFAULT_FALLBACK = ["AI트렌드", "AI서비스"]
