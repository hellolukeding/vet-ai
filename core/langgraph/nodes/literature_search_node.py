"""
文献搜索节点 - 在诊断前搜索相关医学文献
"""
import json
from typing import Dict, List

from config.logger import logger
from core.langgraph.state import LiteratureItem, VetAgentState
from core.langgraph.tools import fetch_webpage_tool, web_search_tool


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
        f"宠物 {description} 兽医诊断",
        f"狗狗 {description} 症状治疗",
        f"猫咪 {description} 病因分析",
    ]

    logger.info(f"开始文献搜索: {description}")

    all_literature = []
    seen_urls = set()  # 避免重复

    try:
        for query in search_queries[:2]:  # 最多执行2个查询以控制时间
            try:
                results_raw = web_search_tool.invoke({
                    "query": query,
                    "num_results": 3,  # 每个查询获取3个结果
                    "use_baidu": use_baidu
                })

                results = json.loads(results_raw) if isinstance(results_raw, str) else results_raw

                if not results:
                    continue

                for r in results[:3]:
                    url = r.get("link", "")
                    # 跳过已见过的URL
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
                            content = content_raw if isinstance(content_raw, str) else str(content_raw)

                            # 限制内容长度避免token浪费
                            if len(content) > 2000:
                                content = content[:2000] + "..."

                    except Exception as e:
                        logger.debug(f"获取网页内容失败: {url}, {e}")

                    literature_item = LiteratureItem(
                        title=title,
                        snippet=snippet,
                        url=url,
                        content=content
                    )
                    all_literature.append(literature_item)

            except Exception as e:
                logger.warning(f"搜索查询失败 [{query}]: {e}")
                continue

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
