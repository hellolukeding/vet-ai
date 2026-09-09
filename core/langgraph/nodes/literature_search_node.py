"""
文献搜索节点 - 在诊断前搜索相关医学文献
"""

import asyncio
import json
from typing import Dict, List

from config.logger import logger
from core.langgraph.state import LiteratureItem, VetAgentState
from core.langgraph.tools import fetch_webpage_tool, web_search_tool
from core.langgraph.tools.web_search import is_trusted_veterinary_source


async def LiteratureSearchNode(state: VetAgentState) -> Dict[str, List[LiteratureItem]]:
    """在诊断前搜索相关医学文献和参考资料

    Args:
        state: VetAgentState with description

    Returns:
        dict with literature key containing list of LiteratureItem
    """
    description = getattr(state, "description", "") or state.get("description", "")

    if not description:
        logger.warning("文献搜索：症状描述为空")
        return {"literature": []}

    # 使用百度搜索中文兽医医学资源（质量更好）
    use_baidu = True

    # 构建搜索查询 - 针对兽医医学场景优化
    search_queries = [
        f"宠物 {description} 兽医 鉴别诊断",
        f"宠物 {description} 小动物 临床检查",
    ]

    logger.info(f"开始文献搜索: {description}")

    async def search(query: str) -> list[LiteratureItem]:
        try:
            raw = await web_search_tool.ainvoke(
                {"query": query, "num_results": 3, "use_baidu": use_baidu}
            )
            results = json.loads(raw) if isinstance(raw, str) else raw
            usable = [r for r in (results or [])[:3] if is_trusted_veterinary_source(r)]

            async def to_item(result: dict) -> LiteratureItem:
                content = ""
                try:
                    if result.get("id"):
                        fetched = await fetch_webpage_tool.ainvoke(
                            {"result_id": result["id"]}
                        )
                        content = str(fetched)[:2000]
                except Exception as exc:
                    logger.debug("获取网页内容失败: {}, {}", result.get("link"), exc)
                return LiteratureItem(
                    title=result.get("title", ""),
                    snippet=result.get("snippet", ""),
                    url=result.get("link", ""),
                    content=content,
                )

            return list(await asyncio.gather(*(to_item(r) for r in usable)))
        except Exception as exc:
            logger.warning("搜索查询失败 [{}]: {}", query, exc)
            return []

    all_literature = []
    seen_urls = set()

    try:
        batches = await asyncio.gather(*(search(query) for query in search_queries))
        for item in (item for batch in batches for item in batch):
            if item.url and item.url not in seen_urls:
                seen_urls.add(item.url)
                all_literature.append(item)

        logger.info(f"文献搜索完成，获取 {len(all_literature)} 条参考")

    except Exception as e:
        logger.error(f"文献搜索过程发生错误: {e}", exc_info=True)
        return {"literature": []}

    # 限制返回数量，避免token过多
    max_literature = 10
    if len(all_literature) > max_literature:
        all_literature = all_literature[:max_literature]
        logger.info(f"文献搜索结果截取为前 {max_literature} 条")

    return {"literature": all_literature}
