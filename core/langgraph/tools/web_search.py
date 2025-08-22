#!/usr/bin/env python3
import json
import os
import time
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# 用户代理
USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# 全局搜索结果缓存
search_results: Dict[str, Dict] = {}


def generate_id(prefix="result"):
    return f"{prefix}_{int(time.time() * 1000)}"


def extract_search_results(html: str, query: str, num_results: int = 5, engine: str = "bing") -> List[Dict]:
    soup = BeautifulSoup(html, "html.parser")
    results = []

    if engine == "bing":
        selector = "#b_results > li.b_algo"
        title_selector = "h2 a"
        snippet_selector = ".b_caption p"
    elif engine == "baidu":
        selector = "div.result, div.c-container"
        title_selector = "h3 a"
        snippet_selector = "div.c-abstract"

    for idx, element in enumerate(soup.select(selector)):
        if len(results) >= num_results:
            break
        title_tag = element.select_one(title_selector)
        snippet_tag = element.select_one(snippet_selector)

        title = title_tag.get_text(strip=True) if title_tag else ""
        link = title_tag["href"] if title_tag and title_tag.has_attr(
            "href") else ""
        snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

        if not title and not snippet:
            continue

        # 百度特殊处理跳转链接
        if engine == "baidu" and link.startswith("/url?"):
            link = requests.get(
                link, headers={"User-Agent": USER_AGENT}, timeout=10).url

        if link and not link.startswith("http"):
            if engine == "bing":
                link = f"https://cn.bing.com{link}"
            elif engine == "baidu":
                link = f"https://www.baidu.com{link}"

        result_id = generate_id(engine)
        result = {"id": result_id, "title": title,
                  "link": link, "snippet": snippet}
        search_results[result_id] = result
        results.append(result)

    if not results:
        fallback_id = generate_id(f"{engine}_fallback")
        fallback_result = {
            "id": fallback_id,
            "title": f"{engine.upper()}搜索结果: {query}",
            "link": f"https://www.baidu.com/s?wd={query}" if engine == "baidu" else f"https://cn.bing.com/search?q={query}",
            "snippet": f"未能解析关于 '{query}' 的搜索结果，您可以直接访问搜索页面查看。"
        }
        search_results[fallback_id] = fallback_result
        results.append(fallback_result)

    return results


def extract_page_content(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "iframe", "noscript", "header", "footer", "nav"]):
        tag.decompose()

    main_selectors = [
        "main", "article", ".article", ".post", ".content", "#content",
        ".main", "#main", ".body", "#body", ".entry", ".entry-content",
        ".post-content", ".article-content", ".text", ".detail"
    ]

    content = ""
    for selector in main_selectors:
        elem = soup.select_one(selector)
        if elem:
            content = elem.get_text(separator="\n", strip=True)
            if len(content) > 100:
                break

    if not content or len(content) < 100:
        paragraphs = [p.get_text(strip=True) for p in soup.find_all(
            "p") if len(p.get_text(strip=True)) > 20]
        if paragraphs:
            content = "\n\n".join(paragraphs)

    if not content:
        content = soup.get_text(separator="\n", strip=True)

    title = soup.title.string if soup.title else ""
    if title:
        content = f"标题: {title}\n\n{content}"

    max_len = 8000
    if len(content) > max_len:
        content = content[:max_len] + "... (内容已截断)"

    return content

# ----------------- LangGraph 工具 -----------------


class Web_Search_Tool(BaseModel):
    query: str = Field(description="搜索关键词")
    num_results: Optional[int] = Field(default=5, description="返回的搜索结果数量")
    use_baidu: Optional[bool] = Field(default=False, description="是否使用百度搜索")


@tool("web_search_tool", args_schema=Web_Search_Tool, return_direct=False)
def web_search_tool(query: str, num_results: int = 5, use_baidu: bool = False):
    """使用必应或百度搜索指定关键词，返回标题、链接和摘要
    args:
        query: 搜索关键词
        num_results: 返回的搜索结果数量
        use_baidu: 是否使用百度搜索
    """
    if use_baidu:
        url = f"https://www.baidu.com/s?wd={query}"
        engine = "baidu"
    else:
        url = f"https://cn.bing.com/search?q={query}&setlang=zh-CN&ensearch=0"
        engine = "bing"

    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        # 处理HTTP错误，如403 Forbidden
        error_msg = f"搜索请求失败: {str(e)}"
        print(error_msg)
        # 返回一个包含错误信息的结果
        error_result = {
            "id": generate_id("error"),
            "title": "搜索请求失败",
            "link": url,
            "snippet": f"无法访问搜索结果: {str(e)}"
        }
        return json.dumps([error_result], ensure_ascii=False, indent=2)
    except requests.exceptions.RequestException as e:
        # 处理其他网络请求错误
        error_msg = f"网络请求错误: {str(e)}"
        print(error_msg)
        # 返回一个包含错误信息的结果
        error_result = {
            "id": generate_id("error"),
            "title": "网络请求错误",
            "link": url,
            "snippet": f"请求过程中发生错误: {str(e)}"
        }
        return json.dumps([error_result], ensure_ascii=False, indent=2)

    results = extract_search_results(resp.text, query, num_results, engine)
    return json.dumps(results, ensure_ascii=False, indent=2)


class Fetch_Webpage_Tool(BaseModel):
    result_id: str = Field(description="搜索结果ID")


@tool("fetch_webpage_tool", args_schema=Fetch_Webpage_Tool, return_direct=False)
def fetch_webpage_tool(result_id: str):
    """根据搜索结果ID获取网页内容
    args:
        result_id: 搜索结果的唯一标识符
    """
    if result_id not in search_results:
        raise ValueError(f"找不到ID为 {result_id} 的搜索结果")
    url = search_results[result_id]["link"]
    headers = {"User-Agent": USER_AGENT, "Referer": "https://cn.bing.com/"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        # 处理HTTP错误，如403 Forbidden
        error_msg = f"获取网页内容失败: {str(e)}"
        print(error_msg)
        return f"无法获取网页内容: {str(e)}"
    except requests.exceptions.RequestException as e:
        # 处理其他网络请求错误
        error_msg = f"网络请求错误: {str(e)}"
        print(error_msg)
        return f"请求过程中发生错误: {str(e)}"

    content = extract_page_content(resp.text)
    return content
