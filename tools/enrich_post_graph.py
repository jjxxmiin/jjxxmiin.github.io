#!/usr/bin/env python3
"""Maintain post descriptions and contextual internal-reading links.

The script never invents article claims. It reuses each post's existing title,
summary, tags and categories to connect closely related articles. Run with
``--write`` after adding or substantially editing posts; without it, the script
reports the changes that would be made and exits non-zero when work is pending.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import re
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import yaml


FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
LINK_BLOCK = re.compile(
    r"\n?<!-- internal-links:start -->.*?<!-- internal-links:end -->\n?",
    re.DOTALL,
)
POST_URL = re.compile(r"\{%\s*post_url\s+([^\s%]+)\s*%\}")
SOURCE_BLOCK = re.compile(
    r"\n?<!-- primary-sources:start -->.*?<!-- primary-sources:end -->\n?",
    re.DOTALL,
)
LONG_IMAGE_WITH_CAPTION = re.compile(
    r"!\[([^\]\n]{181,})\]\(([^)\n]+)\)(\s*\n\*([^*\n]{3,180})\*)"
)
KEYCAP_MARKER = re.compile(r"([0-9])\ufe0f?\u20e3")
DECORATIVE_EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]\ufe0f?")
INSERT_BEFORE = re.compile(
    r"(?m)^##\s+(?:자주 묻는 질문|FAQ(?:\s|$)|References(?:\s|$)|참고(?:문헌| 자료| 링크|$)|출처(?:\s|$))"
)
WORDS = re.compile(r"[0-9A-Za-z가-힣][0-9A-Za-z가-힣+.#-]*")
STOP_WORDS = {
    "a",
    "ai",
    "an",
    "and",
    "about",
    "agent",
    "agentic",
    "agents",
    "analysis",
    "approach",
    "architecture",
    "are",
    "as",
    "at",
    "be",
    "beyond",
    "by",
    "can",
    "deep",
    "developer",
    "developers",
    "dive",
    "does",
    "end",
    "engineering",
    "era",
    "for",
    "framework",
    "from",
    "guide",
    "how",
    "in",
    "inside",
    "into",
    "is",
    "it",
    "method",
    "methods",
    "model",
    "models",
    "my",
    "new",
    "no",
    "not",
    "of",
    "on",
    "or",
    "our",
    "over",
    "perspective",
    "review",
    "system",
    "systems",
    "technical",
    "that",
    "the",
    "this",
    "to",
    "toward",
    "towards",
    "true",
    "using",
    "via",
    "was",
    "were",
    "what",
    "with",
    "without",
    "why",
    "your",
    "그리고",
    "가이드",
    "구조",
    "기술",
    "대해",
    "대한",
    "분석",
    "사용법",
    "시대",
    "실제",
    "아키텍처",
    "에서",
    "원리",
    "위한",
    "으로",
    "이유",
    "정리",
    "하는",
    "방법",

    # Search-style title boilerplate is not a topical relationship.  Keeping
    # these words would connect unrelated articles merely because both promise
    # a review, checklist, installation guide, or cost comparison.
    "가능한",
    "100만",
    "ai는",

    "local",
    "pi",
    "test",
    "token",
    "검증",
    "검증법",
    "결과를",
    "관점에서",
    "공개",
    "기준",
    "기준과",
    "끝낼까",
    "만들까",
    "만든",
    "먼저",
    "모델",
    "모델이",
    "모델을",
    "모델의",
    "무엇부터",
    "문제",
    "발표",
    "비교",
    "보는",
    "설치",
    "실전",
    "실무",
    "쓰나",
    "안전",
    "안전할까",
    "않은",
    "에이전트",
    "에이전트가",
    "에이전트를",
    "에이전트의",
    "완전",
    "원문",
    "운영",
    "움직임",
    "위해",
    "직접",
    "질문",
    "찾는",
    "체크리스트",
    "필요한",
    "탐색",
    "따라",
    "따로",
    "데이터를",
    "돌릴",
    "변환",
    "설정",
    "순서를",
    "연결",
    "최고",
    "한계",
    "활용",
}

# These tags are useful for archives, but one of them alone is not evidence
# that two articles belong in the same three-link reading path.  For example,
# ``컴퓨터비전`` alone must not connect a Darknet loss-layer article to a
# browser-control tool, and ``llm`` alone must not connect every model story.
BROAD_RELATED_TAGS = {
    "ai보안",
    "ai서비스",
    "ai에이전트",
    "ai트렌드",
    "anthropic",
    "api",
    "apple",
    "chatgpt",
    "claude",
    "deepseek",
    "gemini",
    "google",
    "gpt",
    "huggingface",
    "llm",
    "meta",
    "microsoft",
    "nvidia",
    "openai",
    "qwen",
    "xai",
    "강화학습",
    "경량화",
    "논문리뷰",
    "디퓨전모델",
    "로보틱스",
    "멀티모달",
    "멀티에이전트",
    "반도체",
    "벤치마크",
    "아키텍처분석",
    "온디바이스ai",
    "오픈소스",
    "인프라",
    "웹개발",
    "튜토리얼",
    "트랜스포머",
    "파인튜닝",
    "파이썬",
    "프롬프트엔지니어링",
    "컴퓨터비전",
    "음성ai",
}

# Lightweight, explainable content clusters supplement imperfect front-matter
# tags.  They are intentionally based only on titles and summaries, never on
# an existing generated link block, so repeated runs cannot reinforce their
# own recommendations.
TOPIC_PATTERNS = {
    "agent-orchestration": r"langgraph|google\s*adk|agent\s*development\s*kit|multi[ -]?agent|멀티\s*에이전트|subagent|서브에이전트|orchestrat|handoff|agents?\s*sdk|에이전트\s*(?:오케스트레이션|협업)",
    "agent-tool-use": r"google\s*adk|agent\s*development\s*kit|tool[ -]?(?:use|calling)|function\s*calling|도구\s*(?:사용|호출|실행)|툴\s*(?:사용|호출)|액션\s*호출",
    "browser-automation": r"playwright|selenium|browser|chrome|chromium|xpath|(?<![a-z])dom(?![a-z])|scrap(?:ing|er)|crawl(?:ing|er)|브라우저|셀렉터|크롤|스크래핑|접근성\s*트리|웹\s*자동화",
    "coding-agent": r"coding\s*agent|code\s*agent|claude\s*code|aye\s*chat|action-first\s*edit|코딩\s*에이전트|터미널\s*(?:에이전트|ai)|코딩\s*하네스|(?:파일|코드).{0,8}(?:수정|편집)",
    "agent-sandbox": r"opensandbox|cubesandbox|cloudflare\s*computer|agent\s*zero|openhands|sandbox|샌드박스|(?:agent|에이전트).{0,18}(?:docker|격리)|(?:docker|격리).{0,18}(?:agent|에이전트)",
    "cybersecurity": r"cyber|security|pentest|vulnerab|malware|보안|취약점|공격|위협",
    "data-analysis": r"data\s*(?:analysis|formulator|visuali[sz]ation)|(?<![a-z])chart(?![a-z])|데이터\s*분석|차트|시각화|lightgbm|xgboost|pca|lda",
    "design-system": r"design\s*(?:system|token|to[ -]code|sense)|headless\s*design|디자인\s*(?:시스템|토큰|감각)|디자인[ -]코드|(?<![a-z])figma(?![a-z])|component\s*library",
    "diffusion": r"diffusion|diffuseq|(?<![a-z])dit(?![a-z])|디퓨전|확산\s*(?:모델|과정)",
    "distillation": r"distill|teacher.{0,18}student|student.{0,18}teacher|증류|교사\s*모델|학생\s*모델",
    "document-ocr": r"(?<![a-z])ocr(?![a-z])|(?<![a-z])pdf(?![a-z])|document|layout|문서|레이아웃|[표수식]·|표와|수식",
    "efficient-vision": r"efficientnet|efficientdet|bifpn|compound\s*scal|mobilenet|xception|depthwise|model\s*compression|pruning.{0,20}quantization|모델\s*경량화|경량\s*(?:비전|cnn)|모바일\s*(?:비전|cnn)",
    "financial-markets": r"(?<![a-z])trading(?![a-z])|(?<![a-z])trader(?![a-z])|(?<![a-z])stock(?![a-z])|(?<![a-z])backtest|(?<![a-z])quant(?![a-z])|(?<![a-z])hedge(?![a-z])|finance|투자|주식|매매|백테스트|금융|증권",
    "edge-accelerator": r"coral\s*usb|edge\s*tpu|neural\s*compute\s*stick|(?<![a-z])ncs2(?![a-z])|raspberry\s*pi|라즈베리파이|openvino.{0,18}(?:device|추론)",
    "hardware-compute": r"accelerator|(?<![a-z])cpu(?![a-z])|(?<![a-z])gpu(?![a-z])|(?<![a-z])fpga(?![a-z])|(?<![a-z])h100(?![a-z])|(?<![a-z])fp8(?![a-z])|(?<![a-z])gemm(?![a-z])|cuda|데이터\s*센터|데이터센터|전력\s*(?:병목|아키텍처)|병렬처리|멀티코어|가속기|반도체",
    "human-motion-sensing": r"wifi.{0,20}(?:csi|densepose|sensing|센싱|자세)|densepose|(?<![a-z])pose(?![a-z])|자세|인체\s*키포인트|(?:human|사람|인체).{0,20}(?:motion|movement|움직임)|(?:motion|movement|움직임).{0,20}(?:human|사람|인체)",
    "image-generation": r"image\s*(?:generation|editing)|이미지.{0,18}(?:생성|편집|변환|변화|스타일)|(?:전후|참조)\s*이미지|사진\s*(?:생성|편집)|스타일.{0,12}이미지|inpainting|whisk",
    "llm-serving": r"(?<![a-z])vllm(?![a-z])|inference\s*server|serving|llm\s*(?:서빙|배포)|추론\s*서버|로컬\s*llm|양자화",
    "mcp": r"(?<![a-z])mcp(?![a-z])|model\s*context\s*protocol",
    "llm-application": r"llm\s*(?:app|application)|langchain|lobe\s*chat|chatbot\s*ui|챗봇\s*(?:ui|기반)|llm\s*앱|언어\s*모델\s*앱|structured\s*output|구조화\s*출력",
    "llm-safety-alignment": r"(?:llm|language\s*model|언어\s*모델).{0,28}(?:refusal|safety|alignment|거부|안전|정렬)|(?:refusal|decensor|abliterat|거부\s*방향).{0,28}(?:llm|model|모델)",
    "long-video-retrieval": r"long\s*video|긴\s*영상|video.{0,18}(?:retriev|search|qa)|영상.{0,18}(?:검색|질의|qa)|구간\s*검색",
    "creator-video": r"youtube|유튜브|video\s*(?:editing|editor)|영상.{0,12}(?:편집|제작\s*도구)|비디오.{0,12}(?:편집|제작\s*도구)|opencut|openmontage|hyperframes|ffmpeg",
    "creator-workflow": r"youtube|유튜브|opencut|openmontage|hyperframes|video[ -]use|claude\s*code.{0,16}영상|ffmpeg",
    "medical-ai": r"medical|clinical|healthcare|의료|임상",
    "memory-context": r"context\s*(?:window|rot|compression)|memory|메모리|컨텍스트|기억",
    "model-evaluation": r"promptfoo|llm\s*(?:judge|tdd)|(?:gemini|gpt|claude|llm|언어\s*모델).{0,24}(?:benchmark|벤치마크|평가)|(?:benchmark|벤치마크|평가).{0,24}(?:gemini|gpt|claude|llm|언어\s*모델)",
    "model-training": r"nanochat|from\s*scratch|pretrain|pre-training|사전\s*학습|처음부터\s*학습|모델을\s*처음부터",
    "claude-model": r"claude\s*(?:\d|opus|sonnet|haiku|mythos)|anthropic.{0,20}(?:model|모델)|(?:opus|sonnet|haiku|mythos|model\s*2).{0,20}(?:가격|모델|전환|위험)",
    "model-export-runtime": r"tensorflow|savedmodel|frozen\s*(?:pb|graph)|openvino|(?<![a-z])onnx(?![a-z])|tensorrt|모델.{0,12}(?:변환|포팅)|추론.{0,12}(?:런타임|runtime)",
    "multimodal-agent": r"(?=.*(?:multimodal|멀티모달))(?=.*(?:agent|에이전트|(?<![a-z])vla(?![a-z])))",
    "neural-vision": r"convolution|(?<![a-z])cnn(?![a-z])|(?<![a-z])ssd(?![a-z])|(?<![a-z])fsaf(?![a-z])|(?<![a-z])fpn(?![a-z])|default\s*box|anchor|detection|yolo|detectron|darknet|coco\s*api|keypoint|bounding\s*box|객체\s*검출|검출|인스턴스|합성곱|segmentation|세분화|feature\s*pyramid",
    "python-fundamentals": r"decorator|magic\s*method|데코레이터|매직\s*메서드|pep\s*8|serialization|직렬화|json과\s*protobuf",
    "object-tracking": r"kalman|deep\s*sort|(?<![a-z])sort(?![a-z])|re-?id|sam-?2|video\s*object|비디오\s*객체|칼만|객체\s*추적|재식별|트래킹",
    "physical-reasoning": r"physical\s*reasoning|world\s*rules|물리\s*(?:이해|법칙|추론)|물리를\s*검증|물리\s*재현",
    "reinforcement-learning": r"autoaugment|experiential\s*reinforcement|(?<![a-z])erl(?![a-z])|sokoban|reinforcement\s*learning|(?<![a-z])rlvr(?![a-z])|(?<![a-z])grpo(?![a-z])|(?<![a-z])dqn(?![a-z])|q-learning|강화학습|보상\s*모델|policy\s*optimization",
    "research-agent": r"deep\s*research|research\s*agent|perplexica|perplexity|딥\s*리서치|리서치\s*에이전트|연구\s*에이전트",
    "requirements-steering": r"interactive\s*oversight|requirements?\s*(?:elicitation|steering)|prompt\s*(?:design|workflow)|(?<![a-z])prd(?![a-z])|요구사항|질문\s*트리|대화형\s*감독|프롬프트\s*(?:설계|워크플로)|지침으로",
    "retrieval-rag": r"(?<![a-z])rag(?![a-z])|retriev|vector\s*(?:db|database)|벡터\s*(?:db|데이터베이스|검색)|검색\s*증강|임베딩",
    "robot-control": r"vla|robot|로봇|embodied|조작\s*(?:정책|과제)|action\s*(?:model|policy)",
    "semantic-representation": r"nepa|semanticgen|frappe|next\s*embedding|embedding\s*prediction|representation\s*alignment|semantic\s*space|미래\s*표현|다음\s*(?:pixel|픽셀).{0,18}(?:embedding|임베딩)",
    "social-simulation": r"(?<![a-z])oasis(?![a-z])|mirofish|bettafish|tradingagents|social\s*simulation|public\s*opinion|소셜\s*시뮬레이션|에이전트\s*사회|여론",
    "sre-operations": r"opensre|site\s*reliability|pagerduty|incident\s*(?:response|investigation)|장애\s*(?:조사|원인|대응)|운영\s*장애",
    "agent-observability": r"opensre|kibitz|context\s*mode|agent.{0,16}(?:log|observability)|에이전트.{0,16}(?:로그|관측)|조사\s*loop",
    "ebpf-networking": r"(?<![a-z])ebpf(?![a-z])|(?<![a-z])xdp(?![a-z])|cilium|kube-proxy|iptables|sockmap|btf|verifier|사이드카|service\s*mesh|서비스\s*메시",
    "productivity-agent": r"gmail|google\s*calendar|agentic\s*inbox|rowboat|composio|ai\s*coworker|이메일.{0,18}(?:에이전트|자동화)|일정.{0,18}(?:에이전트|자동화)|task.running\s*agent|업무\s*(?:실행|자동화)|로컬.{0,12}코워커",
    "speech-audio": r"(?<![a-z])tts(?![a-z])|speech|voice|audio|음성|오디오|목소리|팟캐스트|음원|음악",
    "speech-recognition": r"(?<![a-z])asr(?![a-z])|speech.to.text|speech recognition|transcri(?:be|ption)|dictation|음성\s*인식|음성\s*전사|받아쓰기",
    "tts-synthesis": r"(?<![a-z])tts(?![a-z])|text.to.speech|speech synthesis|voice clon|음성\s*합성|음성\s*생성|목소리\s*(?:복제|생성)|보이스\s*클로닝",
    "software-engineering": r"swe-lancer|software\s*engineering|소프트웨어\s*과제|코딩\s*(?:능력|과제)|코드\s*구현|저장소.{0,12}(?:수정|구현)|코드\s*리뷰|pull\s*request",
    "small-model": r"small\s*(?:ai|language|general)?\s*model|compact\s*(?:language\s*)?model|소형\s*(?:ai|언어)?\s*모델|경량\s*(?:ai|언어)?\s*모델|작은\s*모델",
    "terminal-cli": r"(?<![a-z])cli(?![a-z])|command[ -]?line|terminal|터미널|명령줄|커맨드라인",
    "video-generation": r"dreamvideo|human\s*video|motion[ -]?controlled|video\s*(?:generation|customization)|text-to-video|인물\s*영상|춤\s*영상|영상\s*(?:생성|편집)|비디오\s*(?:생성|편집)|ai\s*영상|카메라\s*제어",
    "vision-dataset": r"(?=.*(?:image|vision|video|이미지|영상|도로|철도|객체|픽셀|분할))(?=.*(?:dataset|synthetic\s*data|annotation|데이터셋|합성\s*(?:데이터|장애물)|라벨|어노테이션))",
    "vision-reasoning": r"llava|vlm|vision.language|image\s*token|시각\s*(?:추론|질문|언어)|이미지\s*(?:이해|추론|토큰)|visual\s*reasoning",
    "web-application": r"django|web\s*(?:app|application|framework)|http\s*server|warp\s*(?:framework|웹)|(?<![a-z])rest\s*api|frontend|backend|react|redux|node\.js|웹\s*(?:앱|애플리케이션|프레임워크)|프론트엔드|백엔드",
}
COMPILED_TOPIC_PATTERNS = {
    name: re.compile(pattern, re.IGNORECASE)
    for name, pattern in TOPIC_PATTERNS.items()
}
MAX_TOPIC_TOKEN_DOCUMENTS = 12
RELATED_COUNT = 3
DESIRED_MAX_INBOUND = 4

RelatedSignals = tuple[int, int, int, int, int, int]
RelatedMap = dict[str, list[str]]
SignalCache = dict[tuple[str, str], RelatedSignals]


@dataclass
class Post:
    path: Path
    raw: str
    front_raw: str
    body: str
    data: dict
    title: str
    summary: str
    tags: set[str]
    categories: set[str]
    tokens: set[str]
    clusters: set[str]

    @property
    def post_id(self) -> str:
        return self.path.stem

    @property
    def is_public(self) -> bool:
        """Whether Jekyll may expose this post as a related-link target."""
        return (
            self.data.get("published", True) is not False
            and self.data.get("draft", False) is not True
        )


def as_strings(value: object) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, list):
        return {str(item).strip().casefold() for item in value if str(item).strip()}
    return {str(value).strip().casefold()} if str(value).strip() else set()


def title_tokens(title: str, summary: str = "") -> set[str]:
    """Extract human-readable topic terms from search-facing copy.

    The corpus-level document-frequency filter in :func:`load_posts` removes
    both one-off words (which cannot connect two posts) and recurring headline
    boilerplate.  Tags are scored separately and therefore are not injected
    into this set.
    """
    tokens = {
        token.casefold().strip("-+.#")
        for token in WORDS.findall(f"{title} {summary}")
    }
    return {
        token
        for token in tokens
        if len(token) > 1 and not token.isdigit() and token not in STOP_WORDS
    }


def topic_clusters(title: str, summary: str = "", description: str = "") -> set[str]:
    """Return deterministic topical clusters derived from visible metadata."""
    text = " ".join((title, summary, description))
    return {
        name
        for name, pattern in COMPILED_TOPIC_PATTERNS.items()
        if pattern.search(text)
    }


def load_posts(root: Path) -> list[Post]:
    posts: list[Post] = []
    for path in sorted((root / "_posts").glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        match = FRONT_MATTER.match(raw)
        if not match:
            raise ValueError(f"missing front matter: {path}")
        front_raw = match.group(1)
        data = yaml.safe_load(front_raw) or {}
        body = raw[match.end() :]
        title = str(data.get("title") or "").strip()
        summary = str(data.get("summary") or data.get("description") or "").strip()
        posts.append(
            Post(
                path=path,
                raw=raw,
                front_raw=front_raw,
                body=body,
                data=data,
                title=title,
                summary=summary,
                tags=as_strings(data.get("tags")),
                categories=as_strings(data.get("categories")),
                tokens=title_tokens(title, summary),
                clusters=topic_clusters(
                    title,
                    summary,
                    str(data.get("description") or ""),
                ),
            )
        )

    # Only terms shared by a small part of the corpus can express a useful
    # reading-path relation.  This also makes a newly generated article's
    # recommendations independent of existing generated link text.
    document_frequency = collections.Counter(
        token for post in posts if post.is_public for token in post.tokens
    )
    for post in posts:
        post.tokens = {
            token
            for token in post.tokens
            if 2 <= document_frequency[token] <= MAX_TOPIC_TOKEN_DOCUMENTS
        }
    return posts


def related_signals(source: Post, candidate: Post) -> RelatedSignals:
    """Return a deterministic, specificity-first relation score.

    Tier 4 shares at least two concrete tag/cluster signals, tier 3 shares one,
    and tier 2 combines low-frequency title/summary terms with broad taxonomy
    overlap.  Broad tags by themselves and coarse categories such as ``Tech``
    never make a pair related.
    """
    shared_tags = source.tags & candidate.tags
    specific_tags = shared_tags - BROAD_RELATED_TAGS
    broad_tags = shared_tags & BROAD_RELATED_TAGS
    # Do not count the textual spelling of a shared tag as an independent
    # semantic signal.  That would let one generic tag (for example ``qwen``)
    # promote unrelated speech and vision articles simply because both repeat
    # the tag in their summary.
    tokens = (source.tokens & candidate.tokens) - shared_tags
    clusters = source.clusters & candidate.clusters
    strong_signals = len(specific_tags) + len(clusters)
    tier = (
        4
        if strong_signals >= 2
        else 3
        if strong_signals == 1
        else 2
        if tokens
        and broad_tags
        and (len(tokens) >= 2 or len(broad_tags) >= 2)
        else 0
    )
    score = (
        len(specific_tags) * 60
        + len(clusters) * 50
        + len(tokens) * 12
        + len(broad_tags) * 4
    )
    return (
        tier,
        score,
        len(specific_tags),
        len(tokens),
        len(broad_tags),
        len(clusters),
    )


def related_score(source: Post, candidate: Post) -> tuple[int, int, int, str]:
    """Backward-compatible compact score used by callers outside this file."""
    _, score, specific_tags, tokens, _, _ = related_signals(source, candidate)
    return score, specific_tags, tokens, candidate.post_id


def build_signal_cache(posts: list[Post], targets: list[Post]) -> SignalCache:
    return {
        (source.post_id, candidate.post_id): related_signals(source, candidate)
        for source in posts
        for candidate in targets
        if source.post_id != candidate.post_id
    }


def candidate_sort_key(
    source: Post,
    candidate: Post,
    signals: SignalCache | None = None,
    inbound: collections.Counter[str] | None = None,
) -> tuple[int, int, int, int, int, int, int, str]:
    relation = (
        signals[(source.post_id, candidate.post_id)]
        if signals is not None
        else related_signals(source, candidate)
    )
    tier, score, specific, tokens, broad, clusters = relation
    load = inbound[candidate.post_id] if inbound is not None else 0
    return (
        -tier,
        -score,
        -specific,
        -clusters,
        -tokens,
        -broad,
        load,
        candidate.post_id,
    )


def select_related(
    source: Post,
    posts: list[Post],
    count: int = RELATED_COUNT,
    *,
    signals: SignalCache | None = None,
    inbound: collections.Counter[str] | None = None,
) -> list[Post]:
    candidates = [
        candidate
        for candidate in posts
        if (
            candidate.post_id != source.post_id
            and candidate.is_public
            and (
                signals[(source.post_id, candidate.post_id)][0]
                if signals is not None
                else related_signals(source, candidate)[0]
            )
            > 0
        )
    ]
    if len(candidates) < count:
        raise ValueError(
            f"{source.path}: needs {count} distinct public related targets, "
            f"found {len(candidates)}"
        )
    candidates.sort(
        key=lambda candidate: candidate_sort_key(
            source, candidate, signals=signals, inbound=inbound
        )
    )
    return candidates[:count]


def inbound_counts(
    related_map: RelatedMap, public_posts: list[Post]
) -> collections.Counter[str]:
    public_ids = {post.post_id for post in public_posts}
    inbound: collections.Counter[str] = collections.Counter(
        {post_id: 0 for post_id in public_ids}
    )
    for source in public_posts:
        for target in related_map.get(source.post_id, []):
            if target in public_ids:
                inbound[target] += 1
    return inbound


def existing_related_map(
    posts: list[Post], count: int = RELATED_COUNT
) -> tuple[RelatedMap, set[str]]:
    """Read structurally valid existing blocks without changing their order."""
    public_ids = {post.post_id for post in posts if post.is_public}
    related_map: RelatedMap = {}
    invalid: set[str] = set()
    for post in posts:
        match = LINK_BLOCK.search(post.body)
        targets = POST_URL.findall(match.group(0)) if match else []
        valid = (
            len(targets) == count
            and len(set(targets)) == count
            and post.post_id not in targets
            and set(targets) <= public_ids
        )
        if valid:
            related_map[post.post_id] = targets
        else:
            invalid.add(post.post_id)
    return related_map, invalid


def validate_related_map(
    posts: list[Post], related_map: RelatedMap, *, require_coverage: bool
) -> None:
    """Fail before writing if graph invariants do not hold."""
    public_posts = [post for post in posts if post.is_public]
    public_ids = {post.post_id for post in public_posts}
    for source in posts:
        targets = related_map.get(source.post_id, [])
        if len(targets) != RELATED_COUNT:
            raise ValueError(
                f"{source.post_id}: expected {RELATED_COUNT} related targets, "
                f"found {len(targets)}"
            )
        if len(set(targets)) != len(targets):
            raise ValueError(f"{source.post_id}: duplicate related target")
        if source.post_id in targets:
            raise ValueError(f"{source.post_id}: self related-link")
        hidden = set(targets) - public_ids
        if hidden:
            raise ValueError(
                f"{source.post_id}: non-public related target(s): "
                + ", ".join(sorted(hidden))
            )
    if require_coverage:
        inbound = inbound_counts(related_map, public_posts)
        uncovered = sorted(target for target, degree in inbound.items() if degree == 0)
        if uncovered:
            raise ValueError(
                "public posts without inbound related-link: " + ", ".join(uncovered)
            )


def repair_inbound_coverage(
    related_map: RelatedMap,
    public_posts: list[Post],
    signals: SignalCache,
    targets: set[str],
    *,
    preferred_sources: set[str] | None = None,
    minimum_tier: int = 3,
    minimum_score_ratio: float = 0.85,
) -> set[str]:
    """Give requested targets a strong inbound edge when one fits naturally.

    A donor edge is removed only when its old target has at least two inbound
    links, so repairing one zero never creates another.  A repair may not lower
    the relation tier and may lose at most a small fraction of its score.  If no
    such donor exists, the target stays uncovered by this optional widget; tag,
    archive, and sitemap pages still keep it crawlable.
    """
    by_id = {post.post_id: post for post in public_posts}
    inbound = inbound_counts(related_map, public_posts)
    preferred_sources = preferred_sources or set()

    def difficulty(target: str) -> tuple[int, int, str]:
        tiers = [
            signals[(source.post_id, target)][0]
            for source in public_posts
            if source.post_id != target
        ]
        best = max(tiers, default=0)
        return best, sum(tier == best for tier in tiers), target

    changed_sources: set[str] = set()
    for target in sorted(targets, key=difficulty):
        if target not in by_id or inbound[target] > 0:
            continue
        options: list[tuple[tuple, str, str]] = []
        for source in public_posts:
            source_id = source.post_id
            outgoing = related_map.get(source_id, [])
            if (
                len(outgoing) != RELATED_COUNT
                or source_id == target
                or target in outgoing
            ):
                continue
            new_relation = signals[(source_id, target)]
            if new_relation[0] < minimum_tier:
                continue
            for old_target in outgoing:
                if inbound[old_target] <= 1:
                    continue
                old_relation = signals[(source_id, old_target)]
                if new_relation[0] < old_relation[0]:
                    continue
                if new_relation[1] < old_relation[1] * minimum_score_ratio:
                    continue
                delta = new_relation[1] - old_relation[1]
                key = (
                    -new_relation[0],
                    source_id not in preferred_sources,
                    -delta,
                    -new_relation[1],
                    -inbound[old_target],
                    source_id,
                    old_target,
                )
                options.append((key, source_id, old_target))
        if not options:
            continue
        _, source_id, old_target = min(options)
        outgoing = related_map[source_id]
        outgoing[outgoing.index(old_target)] = target
        inbound[old_target] -= 1
        inbound[target] += 1
        changed_sources.add(source_id)
    return changed_sources


def balance_inbound(
    related_map: RelatedMap,
    public_posts: list[Post],
    signals: SignalCache,
    desired_max: int = DESIRED_MAX_INBOUND,
) -> int:
    """Reduce hotspots using only concrete-tag or meaningful-title swaps."""
    inbound = inbound_counts(related_map, public_posts)
    public_ids = set(inbound)
    minimum_possible = math.ceil(
        sum(len(related_map.get(post.post_id, [])) for post in public_posts)
        / max(1, len(public_posts))
    )
    cap = max(desired_max, minimum_possible)
    moves = 0
    while True:
        overloaded = sorted(
            (target for target in public_ids if inbound[target] > cap),
            key=lambda target: (-inbound[target], target),
        )
        if not overloaded:
            break
        underloaded = sorted(
            (target for target in public_ids if inbound[target] < cap),
            key=lambda target: (inbound[target], target),
        )
        moved = False
        for old_target in overloaded:
            options: list[tuple[tuple, str, str]] = []
            for source in public_posts:
                source_id = source.post_id
                outgoing = related_map[source_id]
                if old_target not in outgoing:
                    continue
                old_relation = signals[(source_id, old_target)]
                for new_target in underloaded:
                    if new_target == source_id or new_target in outgoing:
                        continue
                    new_relation = signals[(source_id, new_target)]
                    # Distribution never outranks reader relevance.  Do not
                    # replace a stronger edge or accept a material score loss.
                    if (
                        new_relation[0] < 3
                        or new_relation[0] < old_relation[0]
                        or new_relation[1] < old_relation[1] * 0.85
                    ):
                        continue
                    delta = new_relation[1] - old_relation[1]
                    key = (
                        -new_relation[0],
                        -delta,
                        inbound[new_target],
                        source_id,
                        new_target,
                    )
                    options.append((key, source_id, new_target))
            if not options:
                continue
            _, source_id, new_target = min(options)
            outgoing = related_map[source_id]
            outgoing[outgoing.index(old_target)] = new_target
            inbound[old_target] -= 1
            inbound[new_target] += 1
            moves += 1
            moved = True
            break
        if not moved:
            break
    return moves


def sort_related_map(
    related_map: RelatedMap,
    posts: list[Post],
    signals: SignalCache,
    sources: set[str] | None = None,
) -> None:
    by_id = {post.post_id: post for post in posts}
    for source_id in sorted(sources or set(related_map)):
        if source_id not in related_map:
            continue
        source = by_id[source_id]
        related_map[source_id].sort(
            key=lambda target: candidate_sort_key(
                source, by_id[target], signals=signals
            )
        )


def build_related_map(
    posts: list[Post],
    count: int = RELATED_COUNT,
    desired_max: int = DESIRED_MAX_INBOUND,
) -> RelatedMap:
    """Build a deterministic, relevance-first full-corpus reading map."""
    public_posts = [post for post in posts if post.is_public]
    if len(public_posts) <= count:
        raise ValueError(f"need at least {count + 1} public posts")
    signals = build_signal_cache(posts, public_posts)
    related_map = {
        source.post_id: [
            candidate.post_id
            for candidate in select_related(
                source, public_posts, count=count, signals=signals
            )
        ]
        for source in posts
    }
    inbound = inbound_counts(related_map, public_posts)
    repair_inbound_coverage(
        related_map,
        public_posts,
        signals,
        {target for target, degree in inbound.items() if degree == 0},
    )
    balance_inbound(related_map, public_posts, signals, desired_max=desired_max)
    sort_related_map(related_map, posts, signals)
    validate_related_map(posts, related_map, require_coverage=False)
    return related_map


def build_incremental_related_map(
    posts: list[Post],
    selected_ids: set[str],
    *,
    base_map: RelatedMap | None = None,
    count: int = RELATED_COUNT,
) -> tuple[RelatedMap, set[str], dict[str, int]]:
    """Update selected posts and only the minimum coverage donors.

    Existing valid blocks are preserved byte-for-byte at the map level. A new
    public post necessarily needs one old public source to point to it; that
    donor is the only unselected source this mode permits itself to change.
    """
    public_posts = [post for post in posts if post.is_public]
    by_id = {post.post_id: post for post in posts}
    signals = build_signal_cache(posts, public_posts)
    if base_map is None:
        related_map, invalid = existing_related_map(posts, count=count)
    else:
        related_map = {source: list(targets) for source, targets in base_map.items()}
        invalid = {post.post_id for post in posts if post.post_id not in related_map}

    baseline_inbound = inbound_counts(related_map, public_posts)
    baseline_zero = {
        target for target, degree in baseline_inbound.items() if degree == 0
    }

    # A valid selected block is stable on repeated --only runs. Missing or
    # invalid blocks (the normal new-post case) are created using current load
    # only as the last tie-breaker after topical relevance.
    for source_id in sorted(selected_ids):
        if source_id in related_map and source_id not in invalid:
            continue
        source = by_id[source_id]
        current_inbound = inbound_counts(related_map, public_posts)
        related_map[source_id] = [
            candidate.post_id
            for candidate in select_related(
                source,
                public_posts,
                count=count,
                signals=signals,
                inbound=current_inbound,
            )
        ]

    after_inbound = inbound_counts(related_map, public_posts)
    after_zero = {target for target, degree in after_inbound.items() if degree == 0}
    selected_public = {
        source_id for source_id in selected_ids if by_id[source_id].is_public
    }
    must_cover = (after_zero - baseline_zero) | {
        source_id for source_id in selected_public if after_inbound[source_id] == 0
    }
    donors = repair_inbound_coverage(
        related_map,
        public_posts,
        signals,
        must_cover,
        preferred_sources=selected_ids,
    )
    touched = set(selected_ids) | donors
    sort_related_map(related_map, posts, signals, sources=touched)
    validate_related_map(posts, related_map, require_coverage=False)
    stats = {
        "baseline_zero": len(baseline_zero),
        "requested_coverage": len(must_cover),
        "donors": len(donors - selected_ids),
    }
    return related_map, touched, stats


def related_map_stats(
    posts: list[Post], related_map: RelatedMap
) -> dict[str, int | float]:
    public_posts = [post for post in posts if post.is_public]
    signals = build_signal_cache(posts, public_posts)
    inbound = inbound_counts(related_map, public_posts)
    values = sorted(inbound.values())
    strong = 0
    semantic = 0
    weak = 0
    unrelated = 0
    for source in public_posts:
        for target in related_map.get(source.post_id, []):
            tier = signals[(source.post_id, target)][0]
            strong += tier >= 3
            semantic += tier == 2
            weak += tier == 1
            unrelated += tier == 0
    return {
        "public_posts": len(public_posts),
        "public_edges": sum(values),
        "inbound_min": min(values, default=0),
        "inbound_median": statistics.median(values) if values else 0,
        "inbound_max": max(values, default=0),
        "zero_inbound": sum(value == 0 for value in values),
        "strong_edges": strong,
        "semantic_edges": semantic,
        "weak_edges": weak,
        "unrelated_edges": unrelated,
    }


def compact_summary(text: str, limit: int = 130) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    shortened = text[: limit + 1].rsplit(" ", 1)[0].rstrip(" ,.;:")
    return shortened + "…"


def related_block(related: list[Post]) -> str:
    lines = [
        "<!-- internal-links:start -->",
        "## 함께 읽으면 이해가 이어지는 글",
        "",
    ]
    for post in related:
        description = compact_summary(post.summary)
        suffix = f" — {description}" if description else ""
        # A title is reader data, not Markdown. Escape inline syntax so names
        # such as ``GigaBrain-0.5M*`` cannot swallow the generated link.
        label = re.sub(r"([\\\[\]*_`])", r"\\\1", post.title)
        lines.append(f"- [{label}]({{% post_url {post.post_id} %}}){suffix}")
    lines.extend(["<!-- internal-links:end -->", ""])
    return "\n".join(lines)


def source_links(data: dict) -> list[tuple[str, str]]:
    candidates: list[tuple[str, str]] = []
    if data.get("github_url"):
        candidates.append(("공식 GitHub 저장소", str(data["github_url"])))
    if data.get("news_source_url"):
        candidates.append(("발표 원문", str(data["news_source_url"])))
    for source in data.get("source_citations") or []:
        if isinstance(source, dict) and source.get("url"):
            candidates.append((str(source.get("name") or "원자료"), str(source["url"])))

    selected: list[tuple[str, str]] = []
    seen: set[str] = set()
    for label, url in candidates:
        if not url.startswith(("https://", "http://")) or url in seen:
            continue
        seen.add(url)
        selected.append((label, url))
    return selected


def primary_source_block(sources: list[tuple[str, str]]) -> str:
    lines = [
        "<!-- primary-sources:start -->",
        "## 원문과 버전 확인",
        "",
    ]
    lines.extend(f"- [{label}]({url})" for label, url in sources)
    lines.extend(["<!-- primary-sources:end -->", ""])
    return "\n".join(lines)


def normalize_heading_levels(body: str) -> tuple[str, bool]:
    """Keep the layout's title as the only H1 and repair H3-only old posts."""
    lines = body.splitlines()
    in_fence = False
    h2_count = 0
    h3_count = 0
    for line in lines:
        if re.match(r"^\s*(?:```|~~~)", line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if re.match(r"^##\s+", line):
            h2_count += 1
        elif re.match(r"^###\s+", line):
            h3_count += 1

    promote_h3 = h2_count <= 1 and h3_count >= 2
    changed = False
    in_fence = False
    updated: list[str] = []
    for line in lines:
        if re.match(r"^\s*(?:```|~~~)", line):
            in_fence = not in_fence
            updated.append(line)
            continue
        if not in_fence and re.match(r"^#\s+", line):
            line = "#" + line
            changed = True
        elif not in_fence and promote_h3 and re.match(r"^#{3,6}\s+", line):
            line = line[1:]
            changed = True
        updated.append(line)
    suffix = "\n" if body.endswith("\n") else ""
    return "\n".join(updated) + suffix, changed


def normalize_image_alts(body: str) -> tuple[str, bool]:
    """Replace screen-reader-hostile paper abstracts with nearby short captions."""

    def replace(match: re.Match[str]) -> str:
        caption = re.sub(r"[`_\[\]]", "", match.group(4))
        caption = re.sub(r"\s+", " ", caption).strip()
        return f"![{caption}]({match.group(2)}){match.group(3)}"

    updated, count = LONG_IMAGE_WITH_CAPTION.subn(replace, body)
    return updated, bool(count)


def reference_label(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.casefold().removeprefix("www.")
    path = parsed.path.casefold()
    if host == "github.com":
        return "GitHub README" if "readme" in path else "GitHub 저장소"
    if host == "arxiv.org":
        return "논문 원문 (arXiv)"
    if "huggingface.co" in host:
        return "Hugging Face 원문"
    if host.startswith("docs.") or "/docs" in path or "/documentation" in path:
        return "공식 문서"
    return f"{host or '외부'} 원문"


def normalize_bare_reference_links(body: str) -> tuple[str, bool]:
    """Turn URL-only list items into descriptive links without touching code."""
    changed = False
    in_fence = False
    lines: list[str] = []
    for line in body.splitlines():
        if re.match(r"^\s*(?:```|~~~)", line):
            in_fence = not in_fence
            lines.append(line)
            continue
        match = None if in_fence else re.match(r"^(\s*[-*]\s+)(https?://\S+)\s*$", line)
        if match:
            url = match.group(2)
            line = f"{match.group(1)}[{reference_label(url)}]({url})"
            changed = True
        lines.append(line)
    suffix = "\n" if body.endswith("\n") else ""
    return "\n".join(lines) + suffix, changed


def add_description(front_raw: str, data: dict) -> tuple[str, bool]:
    if str(data.get("description") or "").strip():
        return front_raw, False
    summary = re.sub(r"\s+", " ", str(data.get("summary") or "")).strip()
    if not summary:
        return front_raw, False
    encoded = json.dumps(compact_summary(summary, 160), ensure_ascii=False)
    lines = front_raw.splitlines()
    insert_at = next(
        (
            index + 1
            for index, line in enumerate(lines)
            if re.match(r"^summary\s*:", line)
        ),
        len(lines),
    )
    # Multi-line YAML summaries continue on indented lines. Insert after them.
    while insert_at < len(lines) and (
        not lines[insert_at] or lines[insert_at][0].isspace()
    ):
        insert_at += 1
    lines.insert(insert_at, f"description: {encoded}")
    return "\n".join(lines), True


def remove_bot_author(front_raw: str) -> tuple[str, bool]:
    updated, count = re.subn(
        r"(?m)^author:\s*['\"]?AI Trend Bot['\"]?\s*\n?", "", front_raw
    )
    return updated.rstrip("\n"), bool(count)


def normalize_hero_alt(front_raw: str, data: dict) -> tuple[str, bool]:
    """Give generic paper/GitHub preview images concise, truthful alt text."""
    image = data.get("image")
    if not isinstance(image, dict):
        return front_raw, False
    path = str(image.get("path") or "")
    current = str(image.get("alt") or "").strip()
    title = str(data.get("title") or "").strip()
    replacement = ""
    if "opengraph.githubassets.com/" in path:
        repository = path.split("/1/", 1)[-1].split("?", 1)[0].strip("/")
        if repository.count("/") >= 1:
            replacement = f"{repository} GitHub 저장소 대표 이미지"
    elif (
        current.casefold() in {"paper thumbnail", "preview image", "thumbnail"}
        and title
    ):
        replacement = f"{title} 논문 대표 이미지"
    elif DECORATIVE_EMOJI.search(current):
        replacement = re.sub(r"\s+", " ", DECORATIVE_EMOJI.sub("", current)).strip()
    if not replacement or replacement == current:
        return front_raw, False

    lines = front_raw.splitlines()
    image_line = next((i for i, line in enumerate(lines) if line == "image:"), None)
    if image_line is None:
        return front_raw, False
    for index in range(image_line + 1, len(lines)):
        line = lines[index]
        if line and not line[0].isspace():
            break
        if re.match(r"^\s+alt\s*:", line):
            indent = re.match(r"^(\s*)", line).group(1)
            lines[index] = f"{indent}alt: {json.dumps(replacement, ensure_ascii=False)}"
            # Some old plain YAML values wrap onto more-indented continuation
            # lines. Once the first line is replaced, those fragments must go.
            end = index + 1
            while end < len(lines):
                following = lines[end]
                if not following.strip():
                    break
                following_indent = len(following) - len(following.lstrip())
                if following_indent <= len(indent):
                    break
                end += 1
            if end > index + 1:
                del lines[index + 1 : end]
            return "\n".join(lines), True
    return front_raw, False


def normalize_keycap_markers(body: str) -> tuple[str, bool]:
    """Use ordinary numbered prose/list markers instead of decorative keycaps."""
    updated, count = KEYCAP_MARKER.subn(r"\1.", body)
    return updated, bool(count)


def insert_related_block(body: str, related: list[Post]) -> str:
    """Replace exactly the generated block while preserving article content."""
    body = LINK_BLOCK.sub("\n", body).rstrip() + "\n"
    block = related_block(related)
    match = INSERT_BEFORE.search(body)
    if match:
        return (
            body[: match.start()].rstrip()
            + "\n\n"
            + block
            + "\n"
            + body[match.start() :]
        )
    return body.rstrip() + "\n\n" + block


def update_post(post: Post, related: list[Post]) -> tuple[str, list[str]]:
    changes: list[str] = []
    front_raw, removed = remove_bot_author(post.front_raw)
    if removed:
        changes.append("author")
    front_data = yaml.safe_load(front_raw) or {}
    front_raw, described = add_description(front_raw, front_data)
    if described:
        changes.append("description")
    front_data = yaml.safe_load(front_raw) or {}
    front_raw, hero_alt_changed = normalize_hero_alt(front_raw, front_data)
    if hero_alt_changed:
        changes.append("hero-alt")

    body = LINK_BLOCK.sub("\n", SOURCE_BLOCK.sub("\n", post.body)).rstrip() + "\n"
    body, image_alts_changed = normalize_image_alts(body)
    if image_alts_changed:
        changes.append("image-alt")
    body, references_changed = normalize_bare_reference_links(body)
    if references_changed:
        changes.append("reference-links")
    body, keycaps_changed = normalize_keycap_markers(body)
    if keycaps_changed:
        changes.append("list-markers")
    body, headings_changed = normalize_heading_levels(body)
    if headings_changed:
        changes.append("headings")
    sources = source_links(post.data)
    if sources:
        source_block = primary_source_block(sources)
        match = INSERT_BEFORE.search(body)
        if match:
            body = (
                body[: match.start()].rstrip()
                + "\n\n"
                + source_block
                + "\n"
                + body[match.start() :]
            )
        else:
            body = body.rstrip() + "\n\n" + source_block
        changes.append("sources")

    body = insert_related_block(body, related)
    changes.append("links")

    updated = f"---\n{front_raw}\n---\n\n{body.lstrip()}"
    return updated, changes


def update_link_block_only(post: Post, related: list[Post]) -> tuple[str, list[str]]:
    """Rewrite a coverage donor without normalizing unrelated article data."""
    match = FRONT_MATTER.match(post.raw)
    if not match:
        raise ValueError(f"missing front matter: {post.path}")
    body = insert_related_block(post.body, related)
    return post.raw[: match.end()] + body, ["links"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--write", action="store_true")
    parser.add_argument(
        "--only",
        action="append",
        type=Path,
        help=(
            "Update this post path (repeatable); existing links stay fixed except "
            "for the minimum donor swap needed to give a new public post inbound."
        ),
    )
    args = parser.parse_args()

    posts = load_posts(args.root)
    selected: set[Path] | None = None
    if args.only:
        selected = {
            (path if path.is_absolute() else args.root / path).resolve()
            for path in args.only
        }
        available = {post.path.resolve() for post in posts}
        missing = selected - available
        if missing:
            for path in sorted(missing):
                print(f"post not found: {path}", file=sys.stderr)
            return 2

    by_id = {post.post_id: post for post in posts}
    selected_ids = (
        {post.post_id for post in posts if post.path.resolve() in selected}
        if selected is not None
        else set()
    )
    incremental_stats: dict[str, int] = {}
    try:
        if selected is None:
            related_map = build_related_map(posts)
            touched = set(by_id)
        else:
            related_map, touched, incremental_stats = build_incremental_related_map(
                posts, selected_ids
            )
    except ValueError as exc:
        print(f"related-map error: {exc}", file=sys.stderr)
        return 2

    pending: list[tuple[Post, str, list[str]]] = []
    for post in posts:
        if post.post_id not in touched:
            continue
        related = [by_id[target] for target in related_map[post.post_id]]
        if selected is None or post.post_id in selected_ids:
            updated, changes = update_post(post, related)
        else:
            updated, changes = update_link_block_only(post, related)
        if updated != post.raw:
            pending.append((post, updated, changes))

    for post, updated, changes in pending:
        print(f"{post.path.relative_to(args.root)}\t{','.join(changes)}")
        if args.write:
            post.path.write_text(updated, encoding="utf-8")

    target_count = len(selected) if selected is not None else len(posts)
    graph_stats = related_map_stats(posts, related_map)
    mode = "incremental" if selected is not None else "full"
    graph_summary = " ".join(f"{key}={value}" for key, value in graph_stats.items())
    incremental_summary = " ".join(
        f"{key}={value}" for key, value in incremental_stats.items()
    )
    print(
        f"mode={mode} posts={len(posts)} targets={target_count} "
        f"touched={len(touched)} pending={len(pending)} write={args.write} "
        f"{graph_summary} {incremental_summary}".rstrip()
    )
    return 0 if args.write or not pending else 1


if __name__ == "__main__":
    sys.exit(main())
