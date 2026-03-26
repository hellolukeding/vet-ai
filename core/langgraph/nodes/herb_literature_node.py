"""
中医文献搜索节点 - 搜索中医古籍和现代中医文献
"""

import json
from typing import Dict, List

from config.logger import logger
from core.langgraph.state_herb import TCMRefItem, TCAgentState
from core.langgraph.tools import fetch_webpage_tool, web_search_tool
from core.langgraph.tools.web_search import is_search_result_usable


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
        f"宠物 {description} 中医辨证",
        f"{description} 中兽医 证型",
        f"{description} 中药 方剂",
    ]

    logger.info(f"开始中医文献搜索: {description}")

    all_literature = []
    seen_urls = set()

    try:
        for query in search_queries[:2]:  # 最多执行2个查询
            try:
                results_raw = web_search_tool.invoke(
                    {"query": query, "num_results": 3, "use_baidu": use_baidu}
                )

                results = (
                    json.loads(results_raw)
                    if isinstance(results_raw, str)
                    else results_raw
                )

                if not results:
                    continue

                for r in results[:3]:
                    if not is_search_result_usable(r):
                        logger.debug(f"跳过不可用中医搜索结果: {r}")
                        continue

                    url = r.get("link", "")
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    title = r.get("title", "")
                    snippet = r.get("snippet", "")

                    # 尝试获取完整内容
                    content = ""
                    try:
                        rid = r.get("id", "")
                        if rid:
                            content_raw = fetch_webpage_tool.invoke(rid)
                            content = (
                                content_raw
                                if isinstance(content_raw, str)
                                else str(content_raw)
                            )

                            # 限制内容长度
                            if len(content) > 2000:
                                content = content[:2000] + "..."

                    except Exception as e:
                        logger.debug(f"获取中医网页内容失败: {url}, {e}")

                    literature_item = TCMRefItem(
                        title=title,
                        content=snippet + "\n" + content if content else snippet,
                    )
                    all_literature.append(literature_item)

            except Exception as e:
                logger.warning(f"中医搜索查询失败 [{query}]: {e}")
                continue

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
