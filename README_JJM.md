### Run locally

```
bundle exec jekyll serve
bundle exec jekyll build
```

### Automated bilingual AI news publishing

- GitHub Actions `Twice Daily Bilingual AI News` runs at 09:00 and 17:00 KST.
- Each run fact-checks one AI trend story, then publishes linked English and Korean editions.
- Pipeline: fresh news discovery → deduplication → editorial selection → direct-source claim ledger → conversational five-section English feature → fact-locked natural Korean localization → credited images collected once and shared by both editions.
- Article shape: three-line summary card → what happened → how it worked → why it matters → what to do → what remains unknown → short FAQ and sources. Repetitive report sections are not published.
- Paired URLs use `/en/news/<story>/` and `/ko/news/<story>/`; reciprocal `hreflang` and in-page language switches connect the same story.
- Image policy: use each source article's declared share image first; create one 1200×630 OPSOAI fallback cover only when no checked source provides a usable image.
- Manual run: `cd automation && GEMINI_API_KEY=... python daily_ai_news_bot.py`
- Tests: `cd automation && python -m unittest -v test_daily_ai_news_bot.py`
