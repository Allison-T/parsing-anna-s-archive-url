#!/usr/bin/env python3
"""
Anna's Archive Wikipedia URL Scraper (Wikipedia API 版)

通过 Wikipedia API 获取页面开头部分的 wikitext，从 infobox 的
`website` / `url` 字段提取官方网址。

依赖: pip install requests
"""

import json
import re
import sys
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

PAGE_TITLE = "Anna's Archive"
WIKI_PAGE_URL = "https://en.wikipedia.org/wiki/Anna%27s_Archive"
WIKI_API_URL = "https://en.wikipedia.org/w/api.php"

USER_AGENT = "AnnaArchive-URL-Monitor/1.0 (https://github.com/your-name/your-repo; your-email@example.com)"

# 只接受 annas-archive.xx 或其子域名
ALLOWED_HOST = re.compile(r"(^|\.)annas-archive\.[a-z]{2,}$", re.IGNORECASE)
MAX_URLS = 10


def fetch_wikitext(title: str = PAGE_TITLE, retries: int = 3) -> str:
    """通过 Wikipedia API 获取页面第 0 段（含 infobox）的 wikitext"""
    params = {
        "action": "parse",
        "page": title,
        "prop": "wikitext",
        "section": 0,
        "format": "json",
        "redirects": 1,
    }
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}

    last_error = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(WIKI_API_URL, params=params, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                raise RuntimeError(f"Wikipedia API 错误: {data['error'].get('info', data['error'])}")

            wikitext = data.get("parse", {}).get("wikitext")
            # format=json 默认返回 {"*": "..."}，formatversion=2 则直接是字符串
            if isinstance(wikitext, dict):
                wikitext = wikitext.get("*")
            if not wikitext:
                raise RuntimeError("API 返回中没有 wikitext")
            return wikitext
        except (requests.RequestException, RuntimeError, ValueError) as e:
            last_error = e
            if attempt < retries:
                wait = 2 * attempt
                print(f"第 {attempt} 次请求失败: {e}，{wait}s 后重试...", file=sys.stderr)
                time.sleep(wait)

    raise RuntimeError(f"获取 wikitext 失败: {last_error}")


def normalize_url(raw: str):
    """校验并规范化 URL，不合法返回 None"""
    try:
        parsed = urlparse(raw.strip())
    except ValueError:
        return None
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return None
    if not ALLOWED_HOST.search(parsed.hostname):
        return None
    return parsed.geturl()


def extract_urls_from_wikitext(wikitext: str) -> list:
    """
    从 infobox 的 `| website =`（或旧的 `| url =`）字段中提取网址。
    提取前先去掉 <ref> 和 HTML 注释，避免误抓引用里的 `url=` 链接。
    返回 [{'url': ..., 'display_text': ...}, ...]
    """
    cleaned = re.sub(r"<!--.*?-->", "", wikitext, flags=re.DOTALL)
    cleaned = re.sub(r"<ref[^>]*/>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<ref[^>]*>.*?</ref>", "", cleaned, flags=re.IGNORECASE | re.DOTALL)

    # 字段值: 从 "| website =" 到下一个 "| xxx =" 行，或单独一行的 "}}"
    field = re.search(
        r"\n\s*\|\s*(?:website|url)\s*=([\s\S]*?)(?=\n\s*\|\s*[\w-]+\s*=|\n\s*\}\})",
        cleaned,
        re.IGNORECASE,
    )
    if not field:
        return []
    block = field.group(1)

    candidates = []  # (url, display_text)

    # 1) {{URL|https://example.com/|可选显示文本}}
    for m in re.finditer(
        r"\{\{\s*URL\s*\|\s*(?:1\s*=\s*)?(https?://[^\s}|]+)\s*(?:\|\s*(?:2\s*=\s*)?([^}|]*))?\}\}",
        block,
        re.IGNORECASE,
    ):
        candidates.append((m.group(1), (m.group(2) or "").strip()))

    # 2) 兜底: 字段里的裸链接 / 方括号链接
    if not candidates:
        for m in re.finditer(r"https?://[^\s}|\]<>]+", block, re.IGNORECASE):
            candidates.append((m.group(0), ""))

    urls, seen = [], set()
    for raw, text in candidates:
        url = normalize_url(raw)
        if not url or url in seen:
            continue
        seen.add(url)
        display = text or urlparse(url).hostname
        urls.append({"url": url, "display_text": display})
        if len(urls) >= MAX_URLS:
            break

    return urls


def save_to_json(data: dict, filename: str = "urls.json"):
    """保存数据为 JSON 格式"""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ 已保存到 {filename}")


def save_to_markdown(data: dict, filename: str = "urls.md"):
    """保存数据为 Markdown 格式"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write("# Anna's Archive 网址列表\n\n")
        f.write(f"> 最后更新时间: {data['last_updated']}\n\n")
        f.write(f"> 数据来源: [{data['source']}]({data['source']})\n\n")

        f.write("## 主要网址\n\n")
        f.write("| 网址 | 显示文本 |\n")
        f.write("|------|----------|\n")

        for info in data["urls"]:
            url = info.get("url", "")
            text = info.get("display_text", "")
            f.write(f"| [{url}]({url}) | {text} |\n")

        f.write("\n---\n\n")
        f.write("## 说明\n\n")
        f.write("此文件由自动化脚本生成，每天自动从 Wikipedia 获取最新信息。\n")

    print(f"✓ 已保存到 {filename}")


def main():
    print(f"正在通过 Wikipedia API 获取: {PAGE_TITLE}")

    try:
        wikitext = fetch_wikitext()
        urls = extract_urls_from_wikitext(wikitext)

        # 提取不到有效网址时直接失败，不覆盖已有文件
        if not urls:
            print("未能提取到有效网址，可能是 Wikipedia 页面结构发生了变化", file=sys.stderr)
            sys.exit(1)

        data = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "source": WIKI_PAGE_URL,
            "urls": urls,
        }

        save_to_json(data, "urls.json")
        save_to_markdown(data, "urls.md")

        print("\n抓取完成!")
        print(f"找到 {len(urls)} 个主要 URL")
        print("\n抓取结果:")
        for info in urls:
            print(f"   - {info['url']} ({info.get('display_text', 'N/A')})")

    except Exception as e:
        print(f"处理失败: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
