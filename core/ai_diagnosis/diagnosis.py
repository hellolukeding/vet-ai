import os
from datetime import datetime

import agentscope
from agentscope.agents import DictDialogAgent
from agentscope.message import Msg
from agentscope.parsers import MarkdownJsonDictParser
from dotenv import load_dotenv

from config.logger import logger


class Diagnosis:
    def __init__(self):
        load_dotenv(".env")
        self.model_name = os.getenv("model_name")
        self.base_url = os.getenv("base_url")
        self.api_key = os.getenv("api_key")
        
        logger.info(f"Model Name: {self.model_name}")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"API Key: {self.api_key}")
    
        agentscope.init(
            model_configs=[
                {
                    "model_type": "openai_chat",
                    "config_name": self.model_name,
                    "model_name": self.model_name,
                    "api_key": self.api_key,
                    "client_args": {
                        "base_url": self.base_url,
                    },
                    "generate_args": {
                        "max_tokens": 4096,
                        "temperature": 0.5,
                        "frequency_penalty": 1.2,
                        "n": 1,
                        "stream": False,
                        "top_p": 0.8,
                    },
                }
            ]
        )

    def diagnosis(self, desc: str) -> str:
        alice = DictDialogAgent(
            name="Alice",
            model_config_name=self.model,
            sys_prompt=f"""
            当前时间为 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}.
            你是宠物医院的 AI 诊断助手，专门为宠物提供健康诊断和建议。
            你的任务是根据宠物的症状描述，提供可能的疾病诊断和治疗建议。
            请确保你的回答简洁明了，避免使用专业术语。
            针对治疗建议，需要提供药品的用法用量。
            同时给出合适的治疗建议
            """,
            max_retries=3,
        )
        parser = MarkdownJsonDictParser(
            content_hint={
                     "disease": "可能的疾病",
                     "base_suggestion": "初步治疗建议",
                     "continuing_suggestion": "持续治疗建议",
                     "suggestion": "最终建议",

            },
            required_keys=["disease", "base_suggestion", "continuing_suggestion", "suggestion"],

        )
        alice.set_parser(parser)
        
        msg = alice(Msg("Bob", f"根据宠物描述判定它的病情：{desc}", "user"))

        return msg.content