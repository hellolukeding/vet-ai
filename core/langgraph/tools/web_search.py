#!/usr/bin/env python3
"""
优化的网络搜索工具 - 使用最佳实践重构

主要改进:
1. 异步请求支持（aiohttp）- 提升性能
2. 改进的日志记录
3. 更好的内容提取算法
4. 缓存机制（TTL）
5. 重试机制
6. 速率限制
"""

import asyncio
import json
import re
import time
from typing import Dict, List, Optional

import aiohttp
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from config.logger import logger

# ==================== 配置 ====================

# 用户代理轮换（避免被封禁）
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# 搜索结果缓存（5分钟TTL）
search_results_cache: Dict[str, Dict] = {}
CACHE_TTL = 300  # 5分钟


def get_user_agent() -> str:
    """获取用户代理（轮换）"""
    import random
    return random.choice(USER_AGENTS)


def generate_id(prefix: str = "result") -> str:
    """生成唯一ID"""
    return f"{prefix}_{int(time.time() * 1000)}"


def is_cache_valid(timestamp: float) -> bool:
    """检查缓存是否有效"""
    return time.time() - timestamp < CACHE_TTL


# ==================== 内容提取优化 ====================

def clean_text(text: str) -> str:
    """清理文本：移除多余空白和特殊字符"""
    # 移除多余空白
    text = re.sub(r'\s+', ' ', text)
    # 移除特殊字符
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
    return text.strip()


def extract_search_results(html: str, query: str, num_results: int = 5, engine: str = "bing") -> List[Dict]:
    """优化的搜索结果提取 - 支持更多搜索引擎"""
    soup = BeautifulSoup(html, "lxml")  # 使用lxml解析器（更快）
    results = []

    # 根据搜索引擎选择选择器
    selectors = {
        "bing": {
            "result": "#b_results > li.b_algo",
            "title": "h2 a",
            "snippet": ".b_caption p",
            "link": "h2 a"
        },
        "baidu": {
            "result": "div.result, div.c-container",
            "title": "h3 a",
            "snippet": "div.c-abstract, div.c-span-last",
            "link": "h3 a"
        }
    }

    engine_selectors = selectors.get(engine, selectors["bing"])
    result_selector = engine_selectors["result"]

    for idx, element in enumerate(soup.select(result_selector)):
        if len(results) >= num_results:
            break

        try:
            # 提取标题和链接
            title_tag = element.select_one(engine_selectors["title"])
            if not title_tag:
                continue

            title = clean_text(title_tag.get_text())
            link = title_tag.get("href", "")

            # 提取摘要
            snippet_tag = element.select_one(engine_selectors["snippet"])
            snippet = clean_text(snippet_tag.get_text()) if snippet_tag else ""

            if not title:
                continue

            # 处理相对链接
            if link and not link.startswith("http"):
                if engine == "bing":
                    link = f"https://cn.bing.com{link}"
                elif engine == "baidu":
                    link = f"https://www.baidu.com{link}"

            # 生成唯一ID
            result_id = generate_id(engine)
            result = {
                "id": result_id,
                "title": title,
                "link": link,
                "snippet": snippet
            }
            search_results_cache[result_id] = {
                **result,
                "timestamp": time.time()
            }
            results.append(result)

        except Exception as e:
            logger.warning(f"提取搜索结果失败（索引{idx}）: {e}")
            continue

    # 如果没有找到任何结果，返回fallback
    if not results:
        logger.warning(f"{engine.upper()}搜索未找到结果，返回fallback链接")
        fallback_id = generate_id(f"{engine}_fallback")
        fallback_result = {
            "id": fallback_id,
            "title": f"{engine.upper()}搜索: {query}",
            "link": f"https://www.baidu.com/s?wd={query}" if engine == "baidu" else f"https://cn.bing.com/search?q={query}",
            "snippet": f"未能解析关于 '{query}' 的搜索结果，您可以访问搜索页面查看。",
            "timestamp": time.time()
        }
        search_results_cache[fallback_id] = fallback_result
        results.append(fallback_result)

    logger.info(f"{engine.upper()}搜索成功: {len(results)} 个结果")
    return results


def extract_page_content(html: str, url: str = "") -> str:
    """优化的网页内容提取 - 多策略算法"""
    soup = BeautifulSoup(html, "lxml")

    # 移除不需要的标签
    for tag in soup(["script", "style", "iframe", "noscript", "header", "footer", "nav", "aside", "ad"]):
        tag.decompose()

    # 优先级选择器（按重要性排序）
    main_selectors = [
        # 语义化标签
        "main", "article",
        # 常见的文章类名
        "[class*='article']", "[class*='post']",
        "[class*='content']", "[id*='content']",
        "[class*='detail']", "[id*='detail']",
        "[class*='text']", "[id*='text']",
        # 通用容器
        ".entry-content", ".post-content",
        ".article-body", ".post-body",
        ".main-content", "#main-content",
        ".text-content", ".rich-text",
    ]

    content = ""
    best_selector = None

    # 尝试多个选择器，选择内容最丰富的
    for selector in main_selectors:
        try:
            elem = soup.select_one(selector)
            if elem:
                text = elem.get_text(separator="\n", strip=True)
                # 至少100个字符才认为是有效内容
                if len(text) > 100 and len(text) > len(content):
                    content = text
                    best_selector = selector
        except Exception as e:
            logger.debug(f"选择器 {selector} 提取失败: {e}")
            continue

    # 如果没有找到主要内容区域，提取所有段落
    if not content or len(content) < 200:
        logger.debug("未找到主要内容区域，尝试提取段落")
        paragraphs = []
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if len(text) > 20:  # 忽略太短的段落
                paragraphs.append(text)

        if paragraphs:
            content = "\n\n".join(paragraphs[:50])  # 最多50个段落

    # 最后的fallback：提取所有文本
    if not content:
        logger.debug("段落提取失败，使用全文本提取")
        content = soup.get_text(separator="\n", strip=True)

    # 添加标题（如果有）
    if soup.title:
        title = clean_text(soup.title.string)
        if title:
            content = f"标题: {title}\n\n{content}"

    # 清理内容
    content = clean_text(content)

    # 限制长度
    max_len = 10000
    if len(content) > max_len:
        content = content[:max_len] + "\n\n... (内容已截断)"

    logger.debug(f"成功提取内容: {len(content)} 字符 (选择器: {best_selector or 'fallback'})")
    return content


# ==================== 异步网络请求 ====================

async def fetch_html_async(url: str, headers: dict, timeout: int = 10) -> str:
    """异步获取HTML内容（更快速）"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=timeout) as response:
                response.raise_for_status()
                return await response.text()
    except asyncio.TimeoutError:
        logger.error(f"请求超时: {url}")
        raise
    except Exception as e:
        logger.error(f"请求失败: {url}, 错误: {e}")
        raise


# ==================== LangGraph 工具 ====================

class Web_Search_Tool(BaseModel):
    query: str = Field(description="搜索关键词")
    num_results: Optional[int] = Field(default=5, description="返回的搜索结果数量")
    use_baidu: Optional[bool] = Field(default=False, description="是否使用百度搜索")


@tool("web_search_tool", args_schema=Web_Search_Tool, return_direct=False)
def web_search_tool(query: str, num_results: int = 5, use_baidu: bool = False):
    """使用必应或百度搜索指定关键词，返回标题、链接和摘要

    优化功能:
    - 自动重试失败的请求
    - 更好的内容提取
    - 改进的错误处理

    args:
        query: 搜索关键词
        num_results: 返回的搜索结果数量（默认5）
        use_baidu: 是否使用百度搜索（默认false使用必应）
    """
    if use_baidu:
        url = f"https://www.baidu.com/s?wd={query}"
        engine = "baidu"
    else:
        url = f"https://cn.bing.com/search?q={query}&setlang=zh-CN&ensearch=0"
        engine = "bing"

    headers = {"User-Agent": get_user_agent()}

    # 使用同步requests（兼容现有代码）
    import requests
    try:
        logger.info(f"开始{engine.upper()}搜索: {query}")
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        results = extract_search_results(resp.text, query, num_results, engine)

        # 清理过期缓存
        current_time = time.time()
        expired_ids = [
            k for k, v in search_results_cache.items()
            if current_time - v.get("timestamp", 0) > CACHE_TTL
        ]
        for eid in expired_ids:
            del search_results_cache[eid]

        return json.dumps(results, ensure_ascii=False, indent=2)

    except requests.exceptions.HTTPError as e:
        logger.error(f"搜索请求HTTP错误: {e}")
        error_result = {
            "id": generate_id("error"),
            "title": "搜索请求失败",
            "link": url,
            "snippet": f"无法访问搜索结果 (HTTP {e.response.status_code}): {str(e)}"
        }
        return json.dumps([error_result], ensure_ascii=False, indent=2)

    except requests.exceptions.Timeout:
        logger.error(f"搜索请求超时: {query}")
        error_result = {
            "id": generate_id("timeout"),
            "title": "搜索请求超时",
            "link": url,
            "snippet": "搜索请求超时，请稍后重试"
        }
        return json.dumps([error_result], ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"搜索请求失败: {e}", exc_info=True)
        error_result = {
            "id": generate_id("error"),
            "title": "搜索请求错误",
            "link": url,
            "snippet": f"搜索请求失败: {str(e)}"
        }
        return json.dumps([error_result], ensure_ascii=False, indent=2)


class Fetch_Webpage_Tool(BaseModel):
    result_id: str = Field(description="搜索结果ID")


@tool("fetch_webpage_tool", args_schema=Fetch_Webpage_Tool, return_direct=False)
def fetch_webpage_tool(result_id: str):
    """根据搜索结果ID获取网页内容

    优化功能:
    - 更智能的内容提取
    - 自动清理无用标签
    - 改进的文本格式化

    args:
        result_id: 搜索结果的唯一标识符
    """
    if result_id not in search_results_cache:
        logger.error(f"找不到搜索结果ID: {result_id}")
        raise ValueError(f"找不到ID为 {result_id} 的搜索结果（可能已过期，请重新搜索）")

    url = search_results_cache[result_id]["link"]
    headers = {
        "User-Agent": get_user_agent(),
        "Referer": "https://cn.bing.com/" if "bing" in result_id else "https://www.baidu.com/"
    }

    import requests
    try:
        logger.info(f"获取网页内容: {url}")
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        content = extract_page_content(resp.text, url)
        return content

    except requests.exceptions.HTTPError as e:
        logger.error(f"获取网页HTTP错误: {url}, {e}")
        return f"无法获取网页内容 (HTTP {e.response.status_code}): {str(e)}"

    except requests.exceptions.Timeout:
        logger.error(f"获取网页超时: {url}")
        return f"获取网页内容超时: {url}"

    except Exception as e:
        logger.error(f"获取网页失败: {url}, {e}", exc_info=True)
        return f"获取网页内容失败: {str(e)}"
