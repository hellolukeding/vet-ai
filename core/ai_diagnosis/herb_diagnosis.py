import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List

import agentscope
from agentscope.agents import DialogAgent
from agentscope.message import Msg
from dotenv import load_dotenv

from config.logger import logger
from utils.parser.table import format_diagnosis_as_json, parse_diagnosis_table


class HerbDiagnosis:
    def __init__(self):
        load_dotenv(".env")
        self.model_name = os.getenv("model_name")
        self.base_url = os.getenv("base_url")
        self.api_key = os.getenv("api_key")
        self.model = self.model_name or "vet-logicstorm-lora"
        self.sys_prompt = None
        self.initialized = False
        self.agent: DialogAgent = None

        logger.info(f"Model Name: {self.model_name}")
        logger.info(f"Base URL: {self.base_url}")
        logger.info(f"API Key: {self.api_key}")

        # 只在模型配置有效时初始化AgentScope
        if self.model_name and self.base_url and self.api_key:
            try:
                agentscope.init(
                    model_configs=[
                        {
                            "model_type": "openai_chat",
                            "config_name": "herb_diagnosis",
                            "model_name": self.model_name,
                            "api_key": self.api_key,
                            "client_args": {
                                "base_url": self.base_url,
                            },
                            "generate_args": {
                                "max_tokens": 2048,
                                "temperature": 0.3,
                                "frequency_penalty": 0.1,
                                "presence_penalty": 0.2,
                                "top_p": 0.9,
                                "stop": ["\n\n", "###", "说明"],
                            },
                        }
                    ]
                )
                self.initialized = True
                self._init_agent()  # 初始化agent
            except Exception as e:
                logger.error(f"AgentScope初始化失败: {e}")
                self.initialized = False
        else:
            logger.warning("模型配置不完整，AgentScope未初始化")
            self.initialized = False
        self._init_prompt()

    def _init_prompt(self) -> None:
        self.sys_prompt = """你是具有执业资格的中兽医师，专门从事动物中医诊疗。请注意：

**重要声明：**
- 本系统仅供参考，不能替代专业兽医师的临床诊断
- 所有诊断建议必须基于中兽医学理论和临床经验
- 任何用药建议都必须在执业兽医师指导下进行
- 紧急情况下应立即就医，不可延误

根据症状描述，请按以下表格格式输出中医辨证分析：

| zhengming | description | p | therapy | base | continue | suggest | base_prescription | base_prescription_usage | continue_prescription | continue_prescription_usage | suggest_prescription | suggest_prescription_usage |
|-----------|-------------|---|---------|------|----------|---------|-------------------|-------------------------|----------------------|----------------------------|---------------------|-------------------------|

字段要求：
- zhengming: 中医证型名称（必须基于经典中兽医理论）
- description: 辨证依据（症状、舌象、脉象等四诊合参的分析）
- p: 诊断可信度（0.1-0.9，考虑信息不完整性）
- therapy: 治则治法（如扶正祛邪、调和营卫等）
- base: 基础调护（饮食起居、环境管理等非药物干预）
- continue: 观察要点（病情变化的关键指标）
- suggest: **强制要求专业兽医诊治的情况**
- base_prescription: 经典方剂（仅供参考，禁止自行用药）
- base_prescription_usage: 用法说明（**必须强调兽医指导**）
- continue_prescription: 调方思路（仅供专业人士参考）
- continue_prescription_usage: 调整原则（**必须专业指导**）
- suggest_prescription: 急症处理思路（**紧急就医为主**）
- suggest_prescription_usage: **立即就医，专业处理**

**输出原则：**
1. 保守谨慎，宁可低估诊断可信度
2. 所有方剂建议都标注"仅供参考，需专业指导"
3. 重症情况必须强调立即就医
4. 不得提供具体剂量，避免误用风险
5. 严格按表格格式，确保信息完整性

请根据症状进行专业中兽医辨证分析："""

    def _init_agent(self) -> None:
        self.agent = DialogAgent(
            name="herb_diagnosis",
            model_config_name="herb_diagnosis",
            sys_prompt=self.sys_prompt,
        )
        
            
    def dialog_diagnosis(self, desc: str) -> List[Dict[str, Any]]:
        if not self.initialized or self.agent is None:
            logger.error("Herb diagnosis agent not properly initialized")
            return []
            
        # 构建负责任的用户消息
        user_message = f"""【中兽医辨证参考】
症状描述：{desc}

**免责声明：本分析仅供专业人士参考，不能替代执业兽医师诊断，任何用药必须在专业指导下进行**

请按表格格式进行中兽医辨证分析，重点强调就医建议："""
        
        task = Msg("User", user_message, "user")
        result = self.agent(task)
        logger.info(f"Raw Result: {result.content}")
        
        # 清理输出内容，只保留表格部分
        cleaned_content = self._clean_response_content(result.content)
        logger.info(f"Cleaned Result: {cleaned_content}")
        
        try:
            dict_res = parse_diagnosis_table(cleaned_content)
            logger.info(f"Parsed Result: {dict_res}")
            
            # 对解析结果进行医学责任校验
            validated_res = self._validate_medical_response(dict_res)
            
            # 直接返回校验后的列表
            if isinstance(validated_res, list) and len(validated_res) > 0:
                return validated_res
            else:
                logger.warning(f"校验后结果无效: {type(validated_res)}, 长度: {len(validated_res) if isinstance(validated_res, list) else 'N/A'}")
                # 返回安全的默认诊断
                return self._get_safe_default_diagnosis()
                
        except Exception as e:
            logger.error(f"解析表格失败: {e}")
            # 返回安全的默认诊断
            return self._get_safe_default_diagnosis()
    
    def _get_safe_default_diagnosis(self) -> List[Dict[str, Any]]:
        """返回安全的默认中医诊断，强调就医的重要性"""
        return [
            {
                "zhengming": "证候待辨",
                "description": "**重要提醒：基于有限的症状描述无法进行准确的中医辨证，强烈建议及时就医**",
                "p": "0.1",
                "therapy": "待专业辨证后确定治法",
                "base": "密切观察宠物状态变化，记录症状详情，准备就医",
                "continue": "持续监测体温、食欲、精神状态和排便情况",
                "suggest": "**立即联系具有中兽医资质的专业兽医师进行四诊合参的全面辨证**",
                "base_prescription": "暂停自行用药",
                "base_prescription_usage": "**禁止自行使用中药，必须在执业中兽医师指导下使用任何方剂**",
                "continue_prescription": "等待专业辨证",
                "continue_prescription_usage": "**所有中药方案必须由执业中兽医师制定**",
                "suggest_prescription": "紧急情况处理",
                "suggest_prescription_usage": "**如出现急性症状请立即就医，不可延误治疗**"
            }
        ]
    
    def _validate_medical_response(self, diagnosis_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """校验医学诊断响应，确保符合医学伦理和安全要求"""
        validated_list = []
        
        for diagnosis in diagnosis_list:
            # 确保诊断可信度不会过高（医学诊断需要谨慎）
            if 'p' in diagnosis:
                try:
                    p_value = float(diagnosis['p'])
                    # 限制最高可信度为0.85，因为仅基于症状描述不能达到确诊标准
                    if p_value > 0.85:
                        diagnosis['p'] = '0.85'
                        logger.warning("诊断可信度过高，已调整为0.85")
                except:
                    diagnosis['p'] = '0.6'  # 默认中等可信度
            
            # 确保所有处方相关字段都包含安全提醒
            prescription_fields = ['base_prescription_usage', 'continue_prescription_usage', 'suggest_prescription_usage']
            for field in prescription_fields:
                if field in diagnosis and diagnosis[field]:
                    if '专业指导' not in diagnosis[field] and '兽医师' not in diagnosis[field]:
                        diagnosis[field] = f"**必须在执业兽医师指导下使用** {diagnosis[field]}"
            
            # 确保就医建议字段强调专业诊疗
            if 'suggest' in diagnosis and diagnosis['suggest']:
                if '就医' not in diagnosis['suggest'] and '兽医' not in diagnosis['suggest']:
                    diagnosis['suggest'] = f"建议及时就诊专业兽医师进行确诊。{diagnosis['suggest']}"
            
            # 为严重症状的处方使用字段添加紧急就医提醒
            if 'suggest_prescription_usage' in diagnosis and diagnosis['suggest_prescription_usage']:
                if '紧急' in diagnosis.get('zhengming', '') or '急' in diagnosis.get('therapy', ''):
                    diagnosis['suggest_prescription_usage'] = "**紧急情况请立即就医，不可延误治疗**"
            
            validated_list.append(diagnosis)
        
        return validated_list
    
    def _clean_response_content(self, content: str) -> str:
        """清理响应内容，只保留表格部分"""
        import re

        logger.info(f"原始内容长度: {len(content)}")
        logger.info(f"原始内容前200字符: {content[:200]}")

        # 如果内容为空，直接返回
        if not content or not content.strip():
            logger.warning("输入内容为空")
            return ""

        # 移除代码块标记
        content = re.sub(r'```[a-zA-Z]*\n?', '', content)
        content = re.sub(r'```', '', content)
        
        # 更温和的清理，只移除明显的非表格内容
        content = re.sub(r'#+.*?\n', '', content)  # 移除markdown标题
        content = re.sub(r'---+', '', content)  # 移除分隔线
        
        # 分割成行
        lines = content.split('\n')
        table_lines = []
        
        logger.info(f"总行数: {len(lines)}")
        
        # 更宽松的表格检测
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # 如果包含表格分隔符，认为是表格行
            if '|' in line:
                parts = line.split('|')
                logger.info(f"第{i}行有{len(parts)}个部分: {line[:100]}")
                # 至少要有3个部分才可能是表格
                if len(parts) >= 3:
                    table_lines.append(line)
                # 或者是分隔行
                elif re.match(r'^[\|\s\-]+$', line):
                    table_lines.append(line)
        
        result = '\n'.join(table_lines)
        logger.info(f"清理后表格行数: {len(table_lines)}")
        logger.info(f"清理后内容: {result[:200] if result else '空'}")
        
        return result