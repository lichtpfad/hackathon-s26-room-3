"""Скачать статью блога sostav.ru и положить текстом в reels/input/.

Отдельный инструмент, а не часть экстрактора: по контракту экстрактор в сеть
не ходит, он работает с уже сохранённым текстом. Здесь единственное место,
где есть выход наружу.

    python reels/tools/fetch_article.py 86369 89284 97142
    python reels/tools/fetch_article.py https://www.sostav.ru/blogs/289407/86369
"""

import argparse
import html
import io
import os
import re
import sys
import urllib.request

BLOG = "https://www.sostav.ru/blogs/289407"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0 Safari/537.36"
CONTENT_MARKER = 'class="bl__content bl-content'
TAIL_MARKER = "Другие материалы блога"


def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()
    return raw.decode("utf-8", errors="replace")


def content_div(page):
    """Вырезать div с телом статьи, считая вложенность."""
    start = page.find(CONTENT_MARKER)
    if start < 0:
        raise ValueError("контейнер статьи не найден — вёрстка страницы изменилась")
    start = page.rfind("<div", 0, start)
    depth = 0
    for m in re.finditer(r"<(/?)div\b", page[start:], re.I):
        depth += -1 if m.group(1) else 1
        if depth == 0:
            return page[start:start + m.end()]
    return page[start:]


def to_text(fragment):
    s = re.sub(r"(?is)<(script|style|svg|noscript).*?</\1>", " ", fragment)
    s = re.sub(r"(?is)<h([1-6])[^>]*>", lambda m: "\n\n" + "#" * int(m.group(1)) + " ", s)
    s = re.sub(r"(?is)</h[1-6]>", "\n\n", s)
    s = re.sub(r"(?is)<li[^>]*>", "\n- ", s)
    s = re.sub(r"(?is)<br[^>]*>", "\n", s)
    s = re.sub(r"(?is)</(p|div|ul|ol|tr|blockquote)>", "\n\n", s)
    s = re.sub(r"(?is)<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ")
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r" *\n *", "\n", s)
    return re.sub(r"\n{3,}", "\n\n", s).strip()


def strip_chrome(body, title):
    """Снять навигацию блога сверху и блок «другие материалы» снизу."""
    lines = body.split("\n")
    dup = next((i for i, l in enumerate(lines)
                if l.strip().lstrip("# ").strip() == title), -1)
    if dup >= 0:
        lines = lines[dup + 1:]
        while lines and (not lines[0].strip() or re.match(r"^\d{4}-\d{2}-\d{2} ", lines[0])):
            lines = lines[1:]
    end = next((i for i, l in enumerate(lines) if TAIL_MARKER in l), len(lines))
    return "\n".join(lines[:end]).strip()


def fetch(article, out_dir):
    url = article if article.startswith("http") else f"{BLOG}/{article}"
    article_id = url.rstrip("/").rsplit("/", 1)[-1]
    page = download(url)
    title = html.unescape(re.search(r"<title>(.*?)</title>", page, re.S).group(1)).strip()
    body = strip_chrome(to_text(content_div(page)), title)
    if not body:
        raise ValueError(f"{article_id}: тело статьи пустое")
    text = f"# {title}\n\nИсточник: {url}\n\n{body}\n"
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"sostav-{article_id}.md")
    io.open(path, "w", encoding="utf-8", newline="\n").write(text)
    return path, len(text), title


def main(argv=None):
    ap = argparse.ArgumentParser(description="скачать статью sostav.ru в reels/input/")
    ap.add_argument("articles", nargs="+", help="id статьи или полный url")
    ap.add_argument("-o", "--out", default="reels/input", help="куда класть (по умолчанию reels/input)")
    args = ap.parse_args(argv)

    failed = 0
    for article in args.articles:
        try:
            path, size, title = fetch(article, args.out)
            print(f"ok  {path} · {size} симв · {title}")
        except Exception as exc:  # сеть, вёрстка, кодировка
            failed += 1
            print(f"нет {article} · {exc}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
