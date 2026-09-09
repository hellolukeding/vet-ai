"""
中医文献搜索节点 - 搜索中医古籍和现代中医文献
"""

import asyncio
import json
from typing import Dict, List

from config.logger import logger
from core.langgraph.state_herb import TCAgentState, TCMRefItem
from core.langgraph.tools import fetch_webpage_tool, web_search_tool
from core.langgraph.tools.web_search import is_trusted_veterinary_source


async def HerbLiteratureSearchNode(state: TCAgentState) -> Dict[str, List[TCMRefItem]]:
    """在中医辨证前搜索相关中医文献和古籍资料

    Args:
        state: TCAgentState with description

    Returns:
        dict with literature key containing list of TCMRefItem
    """
    description = getattr(state, "description", "") or state.get("description", "")

    if not description:
        logger.warning("中医文献搜索：症状描述为空")
        return {"literature": []}

    # 使用百度搜索中文中医医学资源
    use_baidu = True

    # 构建搜索查询 - 针对中医场景优化
    search_queries = [
        f"宠物 {description} 中兽医 辨证",
        f"宠物 {description} 中兽医 方剂",
    ]

    logger.info(f"开始中医文献搜索: {description}")

    async def search(query: str) -> list[tuple[str, TCMRefItem]]:
        try:
            raw = await web_search_tool.ainvoke(
                {"query": query, "num_results": 3, "use_baidu": use_baidu}
            )
            results = json.loads(raw) if isinstance(raw, str) else raw
            usable = [r for r in (results or [])[:3] if is_trusted_veterinary_source(r)]

            async def to_item(result: dict) -> tuple[str, TCMRefItem]:
                content = ""
                try:
                    if result.get("id"):
                        fetched = await fetch_webpage_tool.ainvoke(
                            {"result_id": result["id"]}
                        )
                        content = str(fetched)[:2000]
                except Exception as exc:
                    logger.debug(
                        "获取中医网页内容失败: {}, {}", result.get("link"), exc
                    )
                snippet = result.get("snippet", "")
                return result.get("link", ""), TCMRefItem(
                    title=result.get("title", ""),
                    content=snippet + "\n" + content if content else snippet,
                )

            return list(await asyncio.gather(*(to_item(r) for r in usable)))
        except Exception as exc:
            logger.warning("中医搜索查询失败 [{}]: {}", query, exc)
            return []

    all_literature = []
    seen_urls = set()

    try:
        batches = await asyncio.gather(*(search(query) for query in search_queries))
        for url, item in (item for batch in batches for item in batch):
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_literature.append(item)

        logger.info(f"中医文献搜索完成，获取 {len(all_literature)} 条参考")

    except Exception as e:
        logger.error(f"中医文献搜索过程发生错误: {e}", exc_info=True)
        return {"literature": []}

    # 限制返回数量
    max_literature = 10
    if len(all_literature) > max_literature:
        all_literature = all_literature[:max_literature]
        logger.info(f"中医文献搜索结果截取为前 {max_literature} 条")

    return {"literature": all_literature}
