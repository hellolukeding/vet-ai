"""
中医辨证论治节点 - 根据症状进行中医辨证
"""

import json
from datetime import datetime
from typing import Dict, List

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from config.logger import logger
from core.langgraph.state_herb import TCMZhengmingItem, TCAgentState
from core.llm_factory import create_chat_llm
from utils.json.extract_json_from_markdown import extract_json_from_markdown


class TCMZhengmingSchema(BaseModel):
    """中医证型诊断schema"""

    zhengming_list: List[TCMZhengmingItem] = Field(..., description="中医证型列表")


async def HerbDiagnosisNode(state: TCAgentState) -> Dict[str, List[TCMZhengmingItem]]:
    """根据症状描述进行中医辨证论治

    Args:
        state: TCAgentState with description and literature

    Returns:
        dict with zhengming key containing list of TCMZhengmingItem
    """
    temperature = 0.6

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    description = getattr(state, "description", "") or state.get("description", "")
    literature: List = getattr(state, "literature", []) or state.get("literature", [])

    if not description:
        return {"zhengming": []}

    try:
        llm = create_chat_llm(temperature=temperature)
    except Exception as e:
        logger.error(f"中医辨证节点LLM初始化失败: {e}")
        logger.warning("中医辨证LLM配置不可用，不提供默认证型以确保安全性")
        return {"zhengming": []}

    # 中医辨证系统提示
    system_instructions = f"""
    当前时间：{current_time}
    你是一位资深中兽医专家（中文输出），精通中医基础理论、中医诊断学和中药学。

    ## 任务
    根据症状描述和中医文献参考，进行中医辨证论治。返回严格的JSON。

    ## 辨证步骤（Chain of Thought）
    1. **四诊合参**：分析症状中的寒热虚实表里阴阳
    2. **脏腑辨证**：判断病变脏腑（肝心脾肺肾）
    3. **气血津液**：分析气血津液的病理变化
    4. **外感内伤**：区分外感六淫与内伤七情
    5. **证型判断**：综合辨证，确定主要证型
    6. **治法确定**：根据证型确定治则治法

    ## 输出格式
    JSON: {{"zhengming_list": [{{"zhengming": str, "description": str, "probability": float, "therapy": str}}]}}

    ## 辨证示例
    症状："金毛犬Lucky，食欲不振，精神萎靡，大便稀溏"

    推理过程：
    - 食欲不振、精神萎靡 → 脾胃气虚
    - 大便稀溏 → 脾虚湿盛
    - 金毛犬体质偏虚 → 易致脾胃虚弱
    - 病程长短 → 慢性多为虚证

    期望输出：
    {{
      "zhengming_list": [
        {{"zhengming": "脾胃虚弱夹湿", "description": "基于食欲不振、精神萎靡、大便稀溏等症状，判断为脾胃运化功能失调，湿邪内生，中焦气机不畅", "probability": 0.75, "therapy": "健脾益气，燥湿和胃，调理中焦气机"}},
        {{"zhengming": "脾胃气虚", "description": "以食欲不振、精神萎靡为主，中气不足，运化无力", "probability": 0.65, "therapy": "健脾益气，补中益气"}},
        {{"zhengming": "寒湿困脾", "description": "大便稀溏且可能伴有腹鸣腹痛，寒湿之邪困阻中焦", "probability": 0.50, "therapy": "温中散寒，燥湿健脾"}}
      ]
    }}

    ## 要求
    - 必须输出至少5个中医证型，按概率从高到低排序
    - `zhengming` 为中医证名（如脾胃虚弱、风寒感冒、肝火上炎等）
    - `description` 详细说明辨证依据，引用症状特点
    - `probability` 为 0 到 1 的小数，表示辨证可信度
    - `therapy` 写出治则治法（如健脾益气、疏风清热等）
    - 结合中医理论，使用中医术语
    - 如果有提供的文献参考，请结合文献进行辨证
    - 严格只输出 JSON，不要使用Markdown代码块包装结果
    """

    # 构建包含文献参考的prompt
    human_content = f"症状描述：{description}"

    if literature:
        human_content += "\n\n## 中医文献参考\n"
        for idx, lit in enumerate(literature[:5], 1):
            title = getattr(lit, "title", "") or (
                lit.get("title") if isinstance(lit, dict) else ""
            )
            content = getattr(lit, "content", "") or (
                lit.get("content") if isinstance(lit, dict) else ""
            )
            human_content += f"\n文献{idx}：{title}\n"
            if content:
                human_content += f"内容：{content[:300]}...\n"
        logger.info(f"中医辨证节点使用 {len(literature)} 条文献参考")

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessage(content=system_instructions),
            HumanMessage(content=human_content),
        ]
    )

    # 尝试使用结构化输出
    try:
        logger.info("尝试使用结构化输出进行中医辨证")
        structured_llm = llm.with_structured_output(
            TCMZhengmingSchema, method="json_schema"
        )
        messages = prompt.format_messages()
        response = await structured_llm.ainvoke(messages)
        logger.info(f"中医辨证结构化输出成功: {response}")
    except Exception as e:
        logger.warning(f"结构化输出调用失败: {e}，尝试使用普通 LLM + JSON 解析")
        try:
            messages = prompt.format_messages()
            raw_response = await llm.ainvoke(messages)
            logger.info(f"LLM 原始响应: {raw_response.content[:500]}...")

            content = extract_json_from_markdown(raw_response.content)
            logger.debug(f"提取的 JSON 内容: {content}")
            response = json.loads(content)
            logger.info("JSON 解析成功")
        except Exception as e2:
            logger.error(f"中医辨证调用完全失败: {e2}")
            logger.warning("中医辨证失败，不提供默认证型以确保安全性")
            return {"zhengming": []}

    # 规范化输出
    try:
        if hasattr(response, "model_dump"):
            response = response.model_dump()
            logger.debug(
                f"转换为字典: {list(response.keys()) if isinstance(response, dict) else type(response)}"
            )

        zhengming_list = (
            response.get("zhengming_list") if isinstance(response, dict) else None
        )
        if not isinstance(zhengming_list, list):
            logger.warning(f"zhengming_list 字段不是列表: {type(zhengming_list)}")
            zhengming_list = []

        normalized: List[TCMZhengmingItem] = []
        for item in zhengming_list:
            zhengming = item.get("zhengming", "")
            description = item.get("description", "")
            probability = float(item.get("probability", 0))
            therapy = item.get("therapy", "")
            normalized.append(
                TCMZhengmingItem(
                    zhengming=zhengming,
                    description=description,
                    probability=probability,
                    therapy=therapy,
                )
            )

        logger.info(f"成功规范化 {len(normalized)} 个中医证型")
        return {"zhengming": normalized}

    except Exception as e:
        logger.error(f"中医证型解析失败: {e}", exc_info=True)
        logger.warning("证型解析失败，返回空列表以确保安全性")
        return {"zhengming": []}
