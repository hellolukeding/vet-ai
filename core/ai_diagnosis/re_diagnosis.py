import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import agentscope
from agentscope.agents import ReActAgent
from agentscope.message import Msg
from agentscope.service import (ServiceExecStatus, ServiceResponse,
                                ServiceToolkit, execute_python_code)
from dotenv import load_dotenv

from config.logger import logger
from utils.parser.markdown_json_list_parser import extract_clean_json
from utils.react_tool.toolkit import (extract_json_block,
                                      format_json_diagnosis,
                                      repair_broken_json, return_result)


class ReDiagnosis:
    def __init__(self):
        load_dotenv(".env")
        self.model_name = os.getenv("model_name")
        self.base_url = os.getenv("base_url")
        self.api_key = os.getenv("api_key")
        self.model = self.model_name or "vet-logicstorm-lora"
        self.initialized = False

        if self.model_name and self.base_url and self.api_key:
            try:
                agentscope.init(
                    model_configs=[
                        {
                            "model_type": "openai_chat",
                            "config_name": "diagnosis",
                            "model_name": self.model_name,
                            "api_key": self.api_key,
                            "client_args": {"base_url": self.base_url},
                            "generate_args": {
                                "max_tokens": 4096,
                                "temperature": 0.5,
                                "frequency_penalty": 1.2,
                                "top_p": 0.8,
                            },
                        },
                    ]
                )
                self.initialized = True
                logger.info("AgentScope 初始化成功")
            except Exception as e:
                logger.error(f"AgentScope 初始化失败: {e}")
        else:
            logger.warning("诊断模型配置信息缺失，未能初始化")

        if self.initialized:
            self._init_agent()

    def _init_agent(self) -> None:
        toolkit = ServiceToolkit()
        toolkit.add(extract_json_block, func_description="从文本中提取JSON代码块")
        toolkit.add(format_json_diagnosis, func_description="格式化诊断JSON字符串，修复各种格式问题")
        toolkit.add(return_result, func_description="返回最终结果")
        toolkit.add(execute_python_code, func_description="执行Python代码", timeout=300, use_docker=False)

        sys_prompt = (
            f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "You are a professional veterinary diagnosis assistant.\n"
            "Your task is to extract and structure disease diagnosis from the user's symptom description.\n\n"
            "Please respond with a **valid JSON array**, where each object includes:\n"
            "- \"disease\": the name of the suspected disease (string)\n"
            "- \"p\": probability of correctness (float between 0 and 1)\n"
            "- \"base\": basic home care suggestions\n"
            "- \"continue\": ongoing treatment suggestions\n"
            "- \"suggest\": serious condition suggestions (when to visit the hospital)\n\n"
            "Strict formatting rules:\n"
            "1. Every key and value must be enclosed in ASCII double quotes (\"\")\n"
            "2. No single quotes or Chinese quotes allowed anywhere\n"
            "3. No newlines inside key or value strings\n"
            "4. Do not wrap the JSON in explanations, comments or markdown\n"
            "5. Do not return invalid or incomplete JSON\n"
            "6. If you cannot extract valid information, return an empty array []\n"
            "7. Use Chinese characters for all values\n"
        )

        self.agent = ReActAgent(
            name="DiagnosisAgent",
            model_config_name="diagnosis",
            sys_prompt=sys_prompt,
            service_toolkit=toolkit,
            max_iters=3,
            verbose=True,
        )

    def dialog_diagnosis(self, desc: str) -> List[Dict[str, Any]]:
        """执行宠物症状诊断，返回诊断结果数组"""
        if not self.initialized:
            logger.error("诊断服务未正确初始化")
            return []

        if not desc.strip():
            logger.warning("诊断描述为空")
            return []

        try:
            task = Msg("User", f"症状描述：{desc}", "user")
            result = self.agent(task)

            # 原始模型输出
            raw_output = result.content if isinstance(result.content, str) else result.content.text
            logger.debug(f"模型原始输出: {raw_output[:500]}")

            # 统一提取清洗处理
            json_result: Optional[List[Dict[str, Any]]] = extract_clean_json(raw_output)
            if json_result is None:
                logger.error("最终未能成功解析JSON")
                return []

            return json_result
        except Exception as e:
            logger.error(f"诊断过程中发生异常: {e}", exc_info=True)
            return []
    
