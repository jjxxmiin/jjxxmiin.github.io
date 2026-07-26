"""이전 실행 경로 호환용 래퍼.

오픈소스 Trending 글 자동화는 중단되었고 최신 AI 뉴스 파이프라인으로 이관되었다.
새 워크플로와 수동 실행은 ``daily_ai_news_bot.py``를 사용한다.
"""

from daily_ai_news_bot import main


if __name__ == "__main__":
    main()
