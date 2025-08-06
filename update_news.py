import os, re, html, requests, sys
from pathlib import Path
from urllib.parse import urlencode
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv() 

README_PATH = Path("README.md")
NEWS_START = "<!-- NEWS:START -->"
NEWS_END = "<!-- NEWS:END -->"

CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")
QUERY = os.environ.get("NAVER_QUERY", "기업")
DISPLAY = int(os.environ.get("NAVER_DISPLAY", "10"))  # 1~100
SORT = os.environ.get("NAVER_SORT", "date")  # sim | date

API_URL = "https://openapi.naver.com/v1/search/news.json"

def strip_tags(s: str) -> str:
    # 제목/요약에 섞인 <b> 태그 등 제거 + HTML 언이스케이프
    if not s:
        return ""
    s = html.unescape(s)
    s = re.sub(r"</?b>", "", s, flags=re.IGNORECASE)
    s = re.sub(r"<[^>]+>", "", s)
    return s.strip()

def to_kst(pub_date: str) -> str:
    try:
        dt = parsedate_to_datetime(pub_date)  # tz-aware
        dt_kst = dt.astimezone(ZoneInfo("Asia/Seoul"))
        return dt_kst.strftime("%Y-%m-%d %H:%M:%S KST")
    except Exception:
        return pub_date  # 실패 시 원문 그대로

def build_markdown(items, query):
    # 헤더(업데이트 시각)
    from datetime import datetime, timezone
    now_kst = datetime.now(tz=ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S KST")

    lines = []
    lines.append(f"## 최신 네이버 뉴스: `{query}`")
    lines.append(f"_Last update: {now_kst}_")
    lines.append("")
    lines.append("| 제목 | 원문(originallink) | 네이버 링크 | 발행시각 | 요약 |")
    lines.append("|---|---|---|---|---|")

    for it in items:
        title = strip_tags(it.get("title"))
        originallink = it.get("originallink") or ""
        link = it.get("link") or ""
        description = strip_tags(it.get("description"))
        pub = to_kst(it.get("pubDate") or "")

        # 마크다운 안전 처리
        def md_escape(s: str) -> str:
            return s.replace("|", "\\|").replace("\n", " ").strip()

        title_md = md_escape(title)
        desc_md = md_escape(description)

        origin_md = f"[원문]({originallink})" if originallink else ""
        link_md = f"[네이버]({link})" if link else ""

        lines.append(f"| {title_md} | {origin_md} | {link_md} | {pub} | {desc_md} |")

    lines.append("")
    lines.append("> 데이터 출처: 네이버 검색 뉴스 API")
    return "\n".join(lines)

def update_readme(new_block: str):
    text = README_PATH.read_text(encoding="utf-8")
    if NEWS_START not in text or NEWS_END not in text:
        raise RuntimeError("README.md에 마커(<!-- NEWS:START -->, <!-- NEWS:END -->)가 없습니다.")

    pattern = re.compile(
        rf"({re.escape(NEWS_START)})(.*)({re.escape(NEWS_END)})",
        flags=re.DOTALL
    )
    replaced = pattern.sub(rf"\1\n{new_block}\n\3", text)
    if replaced != text:
        README_PATH.write_text(replaced, encoding="utf-8")
        print("README.md 업데이트 완료")
    else:
        print("변경 사항 없음")

def main():
    if not CLIENT_ID or not CLIENT_SECRET:
        print("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 필요합니다.", file=sys.stderr)
        sys.exit(1)

    params = {
        "query": QUERY,
        "display": min(max(DISPLAY, 1), 100),
        "start": 1,
        "sort": SORT,  # sim | date
    }
    headers = {
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET,
    }

    url = f"{API_URL}?{urlencode(params)}"
    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    data = r.json()
    items = data.get("items", [])

    md = build_markdown(items, QUERY)
    update_readme(md)

if __name__ == "__main__":
    main()
