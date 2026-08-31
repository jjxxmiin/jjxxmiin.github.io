from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _workflow(name: str) -> str:
    return (ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8")


def test_daily_schedule_tolerates_delayed_delivery_and_bounds_work():
    workflow = _workflow("daily_trend.yml")

    assert "date +%-H" not in workflow
    assert "target=$((" not in workflow
    assert "timeout-minutes: 90" in workflow
    assert "AI_NEWS_MAX_CANDIDATES: '3'" in workflow
    assert "for attempt in 1 2 3" not in workflow
    assert "ref: main" in workflow
    assert "^automation: daily_ai_news$" in workflow
    assert "Run automation resilience tests" in workflow
    assert "PYTHONUNBUFFERED: '1'" in workflow
    assert "Enrich and validate the new post" in workflow


def test_keyword_schedule_tolerates_delayed_delivery_and_checks_latest_main():
    workflow = _workflow("keyword_guide.yml")

    assert "date +%-H" not in workflow
    assert "target=$((" not in workflow
    assert "ref: main" in workflow
    assert "^automation: keyword_guide$" in workflow
    assert "Run automation resilience tests" in workflow
    assert "PYTHONUNBUFFERED: '1'" in workflow
    assert "for attempt in 1 2 3" not in workflow
    assert "발행 시도" not in workflow
    assert workflow.count("python guide_bot.py") == 1
    assert "Enrich and validate the new post" in workflow
