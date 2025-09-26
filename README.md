

# 🐾 VET AI - 宠物智能诊断系统

基于 AI 的宠物诊断系统，提供 **智能诊断**、**中医诊断** 和 **复诊建议** 功能。

---

## 🌟 功能特性

- 🩺 **智能诊断**：基于症状描述，提供专业的宠物疾病诊断建议  
- 🌿 **中医诊断**：从中医视角分析宠物健康状态，推荐草药方剂  
- 🔄 **复诊服务**：跟踪治疗效果，动态生成后续诊疗建议  
- 📊 **LangGraph 工作流**：采用多步骤 AI 工作流，实现结构化、可解释的诊断推理

---

## 🚀 快速开始

### 使用 Docker Compose（推荐）

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd vet-ai
   ```

2. **配置环境变量**
   ```bash
   cd docker
   cp .env.example .env
   # 编辑 .env 文件，填入您的 API 密钥等配置
   ```

3. **启动服务**
   ```bash
   docker compose up -d
   ```

4. **验证服务是否运行**
   ```bash
   curl http://localhost:8080/health
   ```

---

### 本地开发

1. **安装依赖**
   ```bash
   uv sync
   ```

2. **启动开发服务器**
   ```bash
   uv run uvicorn backend.api:app --host 0.0.0.0 --port 8080 --reload
   ```

---

## ⚙️ 环境配置

在 `docker/.env` 中配置以下关键变量：

```env
# AI 模型配置
MODEL_NAME=glm-4.5
BASE_URL=https://open.bigmodel.cn/api/paas/v4
API_KEY=your-api-key-here

# 服务配置
DEBUG=false
HOST=0.0.0.0
PORT=8080
SECRET_KEY=your-secret-key
```

> ✅ 请确保 `API_KEY` 有效，否则 AI 诊断将无法工作。

---

## 📡 API 接口文档

### 基础信息

- **Base URL**: `http://localhost:8080`
- **Content-Type**: `application/json`
- **响应格式**: 所有接口返回标准 JSON

---

### 1. 健康检查

**GET** `/health`

检查服务是否正常运行。

**响应示例：**
```json
{
  "status": "healthy",
  "message": "服务运行正常"
}
```

---

### 2. 智能诊断（LangGraph 工作流）

**POST** `/api/v1/vet/diagnose`

基于症状描述，调用 AI 工作流生成多维度诊断与用药建议。

#### 请求参数
```json
{
  "description": "宠物症状描述（建议包含年龄、品种、行为、饮食、症状等）"
}
```

#### 请求示例
```bash
curl -X POST http://localhost:8080/api/v1/vet/diagnose \
  -H "Content-Type: application/json" \
  -d '{
    "description": "我家猫咪这两天不吃东西，精神萎靡，还有点发烧"
  }'
```

#### 响应示例
```json
{
    "description": "四个月小狗，晚上刚到家，到家后吃了点粮一口气喝了三百毫升水，之后兴奋的一直蹦跳转圈，半小时后睡觉，突发呕吐",
    "diagnosis": [
        {
            "symptom": "急性胃扩张",
            "reason": "短时间内大量饮水(300ml)后剧烈活动(蹦跳转圈)，随后突发呕吐",
            "probability": 0.4
        },
        {
            "symptom": "饮食不当",
            "reason": "刚到家后急促进食饮水，加上幼犬消化系统发育不完全",
            "probability": 0.25
        },
        {
            "symptom": "应激反应",
            "reason": "新环境导致兴奋和行为异常，影响消化系统功能",
            "probability": 0.15
        },
        {
            "symptom": "传染病早期",
            "reason": "四月龄幼犬免疫力较低，突发呕吐可能是传染病初期症状",
            "probability": 0.12
        },
        {
            "symptom": "异物摄入",
            "reason": "幼犬在新环境中可能误食异物导致呕吐",
            "probability": 0.08
        }
    ],
    "medications": [
        {
            "symptom": "急性胃扩张",
            "drug_name": "甲氧氯普胺",
            "dosage": "0.2-0.5 mg/kg PO q8h",
            "frequency": "q8h"
        },
        {
            "symptom": "急性胃扩张",
            "drug_name": "雷尼替丁",
            "dosage": "2 mg/kg PO q12h",
            "frequency": "q12h"
        },
        {
            "symptom": "急性胃扩张",
            "drug_name": "奥美拉唑",
            "dosage": "0.5-1 mg/kg PO q24h",
            "frequency": "q24h"
        },
        {
            "symptom": "饮食不当",
            "drug_name": "益生菌",
            "dosage": "按产品说明使用",
            "frequency": "每日一次或两次"
        },
        {
            "symptom": "饮食不当",
            "drug_name": "蒙脱石散",
            "dosage": "每千克体重1-2g，口服，每8小时一次",
            "frequency": "q8h"
        },
        {
            "symptom": "饮食不当",
            "drug_name": "多酶片",
            "dosage": "每千克体重1-2片，口服，每12小时一次",
            "frequency": "q12h"
        },
        {
            "symptom": "应激反应",
            "drug_name": "氟西汀",
            "dosage": "1-2 mg/kg PO q24h",
            "frequency": "q24h"
        },
        {
            "symptom": "应激反应",
            "drug_name": "赛庚啶",
            "dosage": "0.1-0.5 mg/kg PO q12h",
            "frequency": "q12h"
        },
        {
            "symptom": "应激反应",
            "drug_name": "苯二氮卓类药物",
            "dosage": "地西泮 0.2-0.5 mg/kg PO q8-12h",
            "frequency": "q8-12h"
        },
        {
            "symptom": "传染病早期",
            "drug_name": "阿莫西林克拉维酸钾",
            "dosage": "12.5-25 mg/kg PO q12h",
            "frequency": "q12h"
        },
        {
            "symptom": "传染病早期",
            "drug_name": "恩诺沙星",
            "dosage": "5-10 mg/kg PO q24h",
            "frequency": "q24h"
        },
        {
            "symptom": "传染病早期",
            "drug_name": "多西环素",
            "dosage": "5-10 mg/kg PO q12h",
            "frequency": "q12h"
        },
        {
            "symptom": "异物摄入",
            "drug_name": "液体石蜡",
            "dosage": "每千克体重5-10ml，口服，每12小时一次",
            "frequency": "q12h"
        },
        {
            "symptom": "异物摄入",
            "drug_name": "乳果糖",
            "dosage": "每千克体重0.5-1ml，口服，每8小时一次",
            "frequency": "q8h"
        },
        {
            "symptom": "异物摄入",
            "drug_name": "甲氧氯普胺",
            "dosage": "0.2-0.5 mg/kg PO q8h",
            "frequency": "q8h"
        }
    ]
}
```

#### 字段说明

| 字段名        | 类型   | 说明                     |
| ------------- | ------ | ------------------------ |
| `description` | string | 用户输入的病例描述       |
| `diagnosis`   | array  | 可能的诊断列表           |
| `medications` | array  | 对应各诊断的药物治疗方案 |

##### `diagnosis` 对象字段

| 字段名        | 类型   | 说明           |
| ------------- | ------ | -------------- |
| `symptom`     | string | 疾病或症状名称 |
| `reason`      | string | 诊断依据       |
| `probability` | number | 可能性（0–1）  |

##### `medications` 对象字段

| 字段名      | 类型   | 说明                             |
| ----------- | ------ | -------------------------------- |
| `symptom`   | string | 对应的诊断症状                   |
| `drug_name` | string | 药物名称                         |
| `dosage`    | string | 剂量（如 mg/kg）                 |
| `frequency` | string | 用药频率（如 q8h = 每8小时一次） |

---

### 3. 中医诊断

**POST** `/api/v1/vet/herb`

基于中医理论，提供证候辨识与草药方剂建议。

#### 请求参数
```json
{
  "description": "宠物症状描述"
}
```

#### 请求示例
```bash
curl -X POST http://localhost:8080/api/v1/vet/herb \
  -H "Content-Type: application/json" \
  -d '{
    "description": "四个月小狗，晚上刚到家，到家后吃了点粮一口气喝了三百毫升水，之后兴奋的一直蹦跳转圈，半小时后睡觉，突发呕吐"
  }'
```

#### 响应示例
```json
{
  "message": "诊断成功",
  "data": [
    {
      "zhengming": "胃气上逆证",
      "description": "幼犬脾胃功能尚未健全，加之刚到新环境有应激反应...",
      "p": 0.85,
      "therapy": "和胃降逆，理气止呕",
      "base": "暂停喂食喂水4-6小时，保持环境安静温暖...",
      "continue": "观察呕吐次数、呕吐物性状、精神状态...",
      "suggest": "若呕吐频繁、呕吐物带血...应及时就医",
      "base_prescription": "小半夏汤加减",
      "base_prescription_usage": "半夏6g、生姜3片、茯苓9g...",
      "continue_prescription": "若兼有脾胃虚弱，可加四君子汤",
      "continue_prescription_usage": "党参9g、白术6g...",
      "suggest_prescription": "若呕吐剧烈，可先用生姜汁",
      "suggest_prescription_usage": "鲜生姜捣烂取汁，每次2-3滴..."
    }
  ],
  "code": 200
}
```

#### 字段说明

| 字段名    | 类型   | 说明                 |
| --------- | ------ | -------------------- |
| `message` | string | 接口提示信息         |
| `data`    | array  | 中医诊断结果列表     |
| `code`    | number | 状态码（200 = 成功） |

##### `data` 对象字段

| 字段名                        | 类型   | 说明             |
| ----------------------------- | ------ | ---------------- |
| `zhengming`                   | string | 中医证候名称     |
| `description`                 | string | 证候机理与表现   |
| `p`                           | number | 证候概率（0–1）  |
| `therapy`                     | string | 治疗原则         |
| `base`                        | string | 基础护理建议     |
| `continue`                    | string | 后续观察要点     |
| `suggest`                     | string | 异常情况处理建议 |
| `base_prescription`           | string | 基础方剂名称     |
| `base_prescription_usage`     | string | 基础方用法用量   |
| `continue_prescription`       | string | 后续调理方       |
| `continue_prescription_usage` | string | 后续方用法       |
| `suggest_prescription`        | string | 应急方剂         |
| `suggest_prescription_usage`  | string | 应急方用法       |

---

## ⚠️ 注意事项

1. **API 调用限制**：避免高频请求，防止触发限流。
2. **数据安全**：请勿上传含个人隐私或敏感信息的病例。
3. **诊断仅供参考**：AI 建议不能替代兽医诊疗，严重症状请立即就医。
4. **环境变量必须配置**：确保 `.env` 中的 `API_KEY` 和 `BASE_URL` 正确有效。

---

## 🛠 技术栈

| 类别         | 技术/工具                |
| ------------ | ------------------------ |
| 后端框架     | FastAPI                  |
| AI 框架      | LangGraph, AgentScope    |
| 模型支持     | GLM-4.5, OpenAI 兼容 API |
| 容器化       | Docker & Docker Compose  |
| 依赖管理     | UV                       |
| 文档测试工具 | Apifox（兼容 Postman）   |

---

## 📂 项目结构

```
vet-ai/
├── backend/               # FastAPI 应用入口
├── core/
│   ├── ai_diagnosis/      # AI 诊断逻辑（西医/中医）
│   └── langgraph/         # LangGraph 工作流定义
├── config/                # 配置加载与环境变量管理
├── docker/                # Docker Compose 与 .env
└── utils/                 # 通用工具函数
```

---

## 🧩 开发指南：添加新诊断类型

1. 在 `core/ai_diagnosis/` 下创建新诊断模块（如 `tcm_diagnosis.py`）
2. 在 `backend/routers/` 中注册新路由（如 `herb.py`）
3. 更新本 API 文档，说明新接口用法

---

## 🤝 贡献指南

1. Fork 本仓库  
2. 创建功能分支（`git checkout -b feature/xxx`）  
3. 提交代码（`git commit -m "Add xxx"`）  
4. 发起 Pull Request

---

## 📜 许可证

本项目采用 **MIT License** 开源协议。

---

> 💡 **提示**：本系统整合了 Apifox 等现代 API 工具链，支持高效调试与团队协作。  
> 🌐 了解更多：[Apifox 官网](https://apifox.com)

