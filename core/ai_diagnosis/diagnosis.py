import os
from datetime import datetime

import agentscope
from agentscope.agents import DialogAgent, DictDialogAgent
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
        self.model = os.getenv("model_name", "vet-logicstorm-lora")
        
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
                        "temperature": 0.7,
                        "frequency_penalty": 1.2,
                        "n": 1,
                        "top_p": 0.8,                        
                    },
                    
                }
            ]
        )

    def dialog_diagnosis(self, desc: str) -> str:
        sam = DialogAgent(
            name="Alice",
            model_config_name=self.model,
            sys_prompt="你是一个名叫 Alice 的助手。",
            max_retries=3,
        )
        msg = sam(Msg("Bob", f"根据宠物描述判定它的病情：{desc}", "user"))
        logger.info(f"诊断结果: {msg.content}")
        return msg.content
        

    def diagnosis(self, desc: str) -> str:
        alice = DictDialogAgent(
            name="Alice",
            model_config_name=self.model,
            sys_prompt=f"""
            当前时间为 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}.
            你是一个严谨的宠物诊断助手，专门为宠物提供健康诊断和治疗建议。
            你需要判断可能的疾病，并提供治疗建议。
            根据症状描述可能疾病的概率
            """,
            max_retries=3,
        )
        parser = MarkdownJsonDictParser(
            content_hint={
                     "dis": "可能的疾病",
                     "p":"置信度",
                     "base": "初步治疗建议",
                     "continue": "持续治疗建议",
                     "suggest": "重度治疗建议",
            },
            required_keys=["dis", "p", "base", "continue", "suggest"],
        )
        alice.set_parser(parser)
        
        msg = alice(Msg("Bob", f"根据宠物描述判定它的病情：{desc}", "user"))
        logger.info(f"诊断结果: {msg.content}")
        return msg.content

cus_diagnosis = Diagnosis()