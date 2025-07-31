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
def echo_text(text: str) -> ServiceResponse:
    """回显文本"""
    return ServiceResponse(
        status=ServiceExecStatus.SUCCESS,
        content=text
    )


def test_react_agent():
    """测试ReActAgent是否能正常工作"""
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
    service_toolkit.add(echo_text)
    
    # 创建ReActAgent
    agent = ReActAgent(
        name="TestAgent",
        model_config_name="test_model",
        sys_prompt="你是一个测试助手，可以使用echo_text工具回显文本。",
        service_toolkit=service_toolkit,
        max_iters=3,
        verbose=True,
    )
    
    # 创建测试消息
    test_msg = Msg("User", "请使用echo_text工具回显'Hello, World!'", "user")
    
    # 调用agent
    print("开始测试ReActAgent...")
    response = agent(test_msg)
    
    print(f"ReActAgent响应: {response}")
    if hasattr(response, 'content'):
        print(f"响应内容: {response.content}")
    
    return response


if __name__ == "__main__":
    print("开始测试ReActAgent")
    print("=" * 50)
    
    try:
        result = test_react_agent()
        print("测试完成")
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()