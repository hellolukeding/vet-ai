import os
import sys
from pathlib import Path
import json

# 添加项目根目录到系统路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import agentscope
from agentscope.agents import ReActAgent
from agentscope.message import Msg
from agentscope.service import ServiceToolkit, ServiceResponse, ServiceExecStatus


# 定义测试工具函数
def extract_json_block(text: str) -> ServiceResponse:
    """从文本中提取JSON代码块"""
    try:
        import re
        pattern = r"```json\s*([\s\S]*?)```"
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        if matches:
            return ServiceResponse(
                status=ServiceExecStatus.SUCCESS,
                content=matches[0]
            )
        else:
            # 如果没有找到代码块，尝试直接解析整个文本
            return ServiceResponse(
                status=ServiceExecStatus.SUCCESS,
                content=text
            )
    except Exception as e:
        return ServiceResponse(
            status=ServiceExecStatus.ERROR,
            content={"error": str(e), "raw_input": text}
        )


def format_json_diagnosis(raw_json_str: str) -> ServiceResponse:
    """格式化诊断JSON字符串，修复各种格式问题"""
    try:
        import json
        import re
        
        # 检查输入是否为空
        if not raw_json_str or not raw_json_str.strip():
            return ServiceResponse(
                status=ServiceExecStatus.ERROR,
                content={"error": "输入的JSON字符串为空"}
            )
        
        # 如果输入是被引号包裹的字符串，先去除外层引号
        cleaned_input = raw_json_str.strip()
        if cleaned_input.startswith("'") and cleaned_input.endswith("'"):
            cleaned_input = cleaned_input[1:-1]
        elif cleaned_input.startswith('"') and cleaned_input.endswith('"'):
            cleaned_input = cleaned_input[1:-1]
        
        # 清洗JSON字符串
        def clean_json_string(json_str: str) -> str:
            # 修复转义字符问题，特别是换行符
            json_str = json_str.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
            # 修复多余的控制字符
            import re
            json_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', json_str)
            return json_str
        
        cleaned_json = clean_json_string(cleaned_input)
        cleaned_json = cleaned_json.strip()
        
        # 尝试解析
        parsed_result = json.loads(cleaned_json)
        
        # 验证结果是列表
        if not isinstance(parsed_result, list):
            return ServiceResponse(
                status=ServiceExecStatus.ERROR,
                content={"error": "解析结果不是列表类型", "actual_type": type(parsed_result).__name__}
            )
        
        # 验证每个项目
        validated_items = []
        for i, item in enumerate(parsed_result):
            if not isinstance(item, dict):
                continue
                
            # 确保必需字段存在
            required_keys = ["disease", "p", "base", "continue", "suggest"]
            for key in required_keys:
                if key not in item:
                    item[key] = f"缺失的{key}字段"
            
            # 确保置信度在有效范围内
            try:
                item["p"] = float(item["p"])
                if not (0 <= item["p"] <= 1):
                    item["p"] = max(0, min(1, item["p"]))
            except (ValueError, TypeError):
                item["p"] = 0.5
                
            validated_items.append(item)
        
        return ServiceResponse(
            status=ServiceExecStatus.SUCCESS,
            content=validated_items
        )
    except json.JSONDecodeError as e:
        return ServiceResponse(
            status=ServiceExecStatus.ERROR,
            content={"error": f"JSON解析失败: {str(e)}", "raw_input": raw_json_str}
        )
    except Exception as e:
        return ServiceResponse(
            status=ServiceExecStatus.ERROR,
            content={"error": str(e), "raw_input": raw_json_str}
        )


def return_result(result: any) -> ServiceResponse:
    """返回最终结果"""
    return ServiceResponse(
        status=ServiceExecStatus.SUCCESS,
        content=result
    )


def test_react_agent_with_diagnosis_tools():
    """测试ReActAgent使用诊断工具"""
    # 初始化AgentScope
    agentscope.init(
        model_configs=[
            {
                "model_type": "openai_chat",
                "config_name": "test_model",
                "model_name": "moonshotai/Kimi-K2-Instruct",
                "api_key": "ms-d3532402-86de-4e6d-b60d-158e0851895d",
                "client_args": {
                    "base_url": "https://api-inference.modelscope.cn/v1",
                },
            }
        ]
    )
    
    # 创建工具包
    service_toolkit = ServiceToolkit()
    service_toolkit.add(extract_json_block)
    service_toolkit.add(format_json_diagnosis)
    service_toolkit.add(return_result)
    
    # 创建ReActAgent
    agent = ReActAgent(
        name="TestFormatterAgent",
        model_config_name="test_model",
        sys_prompt="""你是一个专业的数据格式化助手，专门负责校验、优化和格式化诊断数据。

你可以使用以下工具函数来完成任务：
1. extract_json_block: 从文本中提取JSON代码块
   - 参数: text (要处理的文本)
   - 返回: 提取的JSON字符串
2. format_json_diagnosis: 格式化诊断JSON字符串，修复各种格式问题
   - 参数: raw_json_str (原始JSON字符串)
   - 返回: 格式化后的诊断列表
3. return_result: 返回最终结果
   - 参数: result (要返回的结果)
   - 返回: 最终结果

工作流程：
1. 首先使用extract_json_block从输入中提取JSON代码块
2. 然后使用format_json_diagnosis格式化诊断JSON
3. 最后使用return_result返回格式化后的结果

输入格式示例：
```json
[
  {{
    "disease": "犬瘟热",
    "p": 0.87,
    "base": "建议静养，保持温暖",
    "continue": "使用抗病毒药物",
    "suggest": "前往医院治疗并输液"
  }}
]
```

输出格式要求：
```json
[
  {{
    "disease": "犬瘟热",
    "p": 0.87,
    "base": "建议静养，保持温暖",
    "continue": "使用抗病毒药物",
    "suggest": "前往医院治疗并输液"
  }}
]
```""".replace("{", "{{").replace("}", "}}"),  # 转义花括号以避免格式化错误
        service_toolkit=service_toolkit,
        max_iters=5,
        verbose=True,
    )
    
    # 创建测试消息
    test_input = '''```json
[
  {
    "disease": "犬瘟热",
    "p": 0.87,
    "base": "建议静养，保持温暖",
    "continue": "使用抗病毒药物",
    "suggest": "前往医院治疗并输液"
  }
]
```'''
    
    test_msg = Msg("User", test_input, "user")
    
    # 调用agent
    print("开始测试ReActAgent处理诊断数据...")
    response = agent(test_msg)
    
    print(f"ReActAgent响应: {response}")
    if hasattr(response, 'content'):
        print(f"响应内容: {response.content}")
    
    return response


if __name__ == "__main__":
    print("开始测试ReActAgent处理诊断数据")
    print("=" * 50)
    
    try:
        result = test_react_agent_with_diagnosis_tools()
        print("测试完成")
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()