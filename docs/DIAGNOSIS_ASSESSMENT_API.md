# AI 诊断评估接口对接文档

本文档适用于以下接口：

- `POST /api/v1/vet/diagnose`：西医诊断
- `POST /api/v1/vet/herb`：中医诊断
- `GET /api/v1/vet/diagnose/task/{task_id}`：查询异步西医诊断
- `GET /api/v1/vet/herb/task/{task_id}`：查询异步中医诊断

在线接口定义：

- Swagger UI：`http://<host>:<port>/api/docs`
- ReDoc：`http://<host>:<port>/api/redoc`
- OpenAPI JSON：`http://<host>:<port>/api/openapi.json`

## 兼容性约定

本次变更只在响应顶层新增 `assessment`。原有的 `message`、`disclaimer`、`data`、`code`，以及 `data` 内部结构保持不变。

- 西医接口的 `data` 仍为对象。
- 中医接口的 `data` 仍为数组，数组项仍包含原有13个字段。
- 调用方可以增量读取 `assessment`，原有 `data` 解析逻辑无需修改。
- `assessment` 不返回空字符串、空数组或 `null`。

## 请求

两个诊断接口使用相同的请求体：

```json
{
  "description": "3岁金毛犬，今天偶尔打喷嚏，精神食欲正常，无呼吸困难"
}
```

同步调用：

```bash
curl -X POST 'http://localhost:8080/api/v1/vet/diagnose' \
  -H 'Content-Type: application/json' \
  -d '{"description":"3岁金毛犬，今天偶尔打喷嚏，精神食欲正常，无呼吸困难"}'
```

异步调用：

```bash
curl -X POST 'http://localhost:8080/api/v1/vet/herb?async_mode=true' \
  -H 'Content-Type: application/json' \
  -d '{"description":"3岁金毛犬，今天偶尔打喷嚏，精神食欲正常，无呼吸困难"}'
```

## `assessment` 字段

```json
{
  "assessment": {
    "status": "completed",
    "emergency": {
      "status": "completed",
      "level": "routine",
      "reasons": ["仅偶发喷嚏，精神和食欲正常，未描述呼吸困难"],
      "action": "继续观察；如果症状持续、频率增加或出现呼吸异常，请联系兽医",
      "missing_information": ["无"]
    },
    "recommended_tests": {
      "status": "completed",
      "items": [
        {
          "name": "基础体格检查",
          "purpose": "检查鼻腔、口腔、呼吸音和生命体征",
          "priority": "conditional",
          "related_findings": ["打喷嚏"],
          "condition": "症状持续、频率增加或出现鼻腔分泌物时"
        }
      ]
    },
    "temporary_care": {
      "status": "completed",
      "actions": ["保持环境通风并减少灰尘、香水和烟雾刺激"],
      "avoid": ["不要自行使用人用感冒药或抗过敏药"],
      "escalation_signs": ["张口呼吸、牙龈发紫、意识异常或症状迅速加重"]
    },
    "warnings": ["本评估仅供辅助，不能替代执业兽医诊断"]
  }
}
```

### 状态枚举

| 字段 | 可选值 | 含义 |
| --- | --- | --- |
| `assessment.status` | `pending`、`completed`、`partial`、`unavailable` | 整体评估状态 |
| 子模块 `status` | `pending`、`completed`、`unavailable` | 子模块状态 |
| `emergency.level` | `emergency`、`urgent`、`routine`、`unknown` | 紧急程度 |
| `priority` | `urgent`、`recommended`、`conditional` | 检查优先级 |

紧急程度含义：

| 值 | 对接含义 |
| --- | --- |
| `emergency` | 存在危及生命的可能，立即前往急诊 |
| `urgent` | 需要尽快就医，通常不建议继续长期观察 |
| `routine` | 暂未识别到急症信号，仍不能视为排除疾病 |
| `unknown` | 信息不足，需根据 `missing_information` 补充资料或联系兽医 |

### 非空规则

- 所有字符串都有实际内容。
- 所有数组至少包含一项。
- 没有缺失信息时，`missing_information` 返回 `["无"]`。
- 没有额外执行条件时，`condition` 返回 `"无附加条件"`。
- 评估生成中时返回 `pending` 内容，不返回空占位字段。
- 模型不可用时返回 `unavailable` 内容，并提供人工分诊和安全处置建议。

## 同步响应

西医接口：

```json
{
  "message": "智能诊断成功",
  "disclaimer": "AI辅助诊断声明",
  "data": {
    "description": "原始症状描述",
    "diagnosis": [],
    "medications": []
  },
  "code": 200,
  "assessment": {
    "status": "completed",
    "emergency": {
      "status": "completed",
      "level": "routine",
      "reasons": ["当前描述未包含急症信号"],
      "action": "继续观察，出现升级指征时及时就医",
      "missing_information": ["无"]
    },
    "recommended_tests": {
      "status": "completed",
      "items": [{
        "name": "基础体格检查",
        "purpose": "确认生命体征和症状来源",
        "priority": "conditional",
        "related_findings": ["当前症状"],
        "condition": "症状持续或加重时"
      }]
    },
    "temporary_care": {
      "status": "completed",
      "actions": ["保持安静并记录症状变化"],
      "avoid": ["不要自行喂药"],
      "escalation_signs": ["呼吸困难、意识异常或迅速恶化"]
    },
    "warnings": ["本评估仅供辅助，不能替代执业兽医诊断"]
  }
}
```

中医接口：

```json
{
  "message": "中医诊断成功",
  "disclaimer": "AI辅助中医诊断声明",
  "data": [
    {
      "zhengming": "证型名称",
      "description": "辨证依据",
      "p": 0.5,
      "therapy": "治则治法",
      "base": "基础护理",
      "continue": "继续观察",
      "suggest": "建议就医",
      "base_prescription": "基础方剂",
      "base_prescription_usage": "基础方剂用法",
      "continue_prescription": "加减方剂",
      "continue_prescription_usage": "加减方剂用法",
      "suggest_prescription": "急救方剂",
      "suggest_prescription_usage": "急救方剂用法"
    }
  ],
  "code": 200,
  "assessment": {
    "status": "completed",
    "emergency": {
      "status": "completed",
      "level": "routine",
      "reasons": ["当前描述未包含急症信号"],
      "action": "继续观察，出现升级指征时及时就医",
      "missing_information": ["无"]
    },
    "recommended_tests": {
      "status": "completed",
      "items": [{
        "name": "基础体格检查",
        "purpose": "确认生命体征和症状来源",
        "priority": "conditional",
        "related_findings": ["当前症状"],
        "condition": "症状持续或加重时"
      }]
    },
    "temporary_care": {
      "status": "completed",
      "actions": ["保持安静并记录症状变化"],
      "avoid": ["不要自行喂药"],
      "escalation_signs": ["呼吸困难、意识异常或迅速恶化"]
    },
    "warnings": ["本评估仅供辅助，不能替代执业兽医诊断"]
  }
}
```

## 异步响应与轮询

提交成功返回 HTTP 202：

```json
{
  "message": "诊断任务已提交，请使用task_id查询结果",
  "data": {
    "task_id": "任务ID",
    "status": "pending"
  },
  "code": 202,
  "assessment": {
    "status": "pending",
    "emergency": {
      "status": "pending",
      "level": "unknown",
      "reasons": ["正在分析症状和危险信号"],
      "action": "评估完成前请持续观察宠物；如出现危险信号请立即急诊",
      "missing_information": ["评估结果正在生成"]
    },
    "recommended_tests": {
      "status": "pending",
      "items": [{
        "name": "检查建议生成中",
        "purpose": "根据症状确定需要优先排查的项目",
        "priority": "conditional",
        "related_findings": ["当前症状描述"],
        "condition": "等待评估完成"
      }]
    },
    "temporary_care": {
      "status": "pending",
      "actions": ["保持宠物安静并持续观察呼吸和意识状态"],
      "avoid": ["不要自行喂药或进行侵入性处置"],
      "escalation_signs": ["呼吸困难、意识异常、持续抽搐、大出血或迅速恶化"]
    },
    "warnings": ["评估正在生成，本结果暂不能替代执业兽医判断"]
  }
}
```

轮询示例：

```bash
curl 'http://localhost:8080/api/v1/vet/diagnose/task/<task_id>'
curl 'http://localhost:8080/api/v1/vet/herb/task/<task_id>'
```

轮询期间 `assessment.status` 可能先变为 `completed`，主诊断任务完成后 `data` 返回原有诊断结果结构。

异步提交和任务查询响应还会在顶层返回新增字段 `task_status`。原有字段及 `data` 类型保持不变：

- `pending`：等待执行，可以继续轮询。
- `processing`：正在执行，可以继续轮询。
- `completed`：执行完成，停止轮询并读取原有 `data`。
- `failed`：执行失败，停止轮询并读取 `message`。
- `expired`：任务不存在或结果已过期，停止轮询。

## 调用方建议

1. 异步调用先读取 `task_status`，遇到 `completed`、`failed` 或 `expired` 立即停止轮询。
2. 读取 `assessment.status`。
3. 再根据 `emergency.level` 决定提示级别。
4. `emergency` 时应优先显示 `emergency.action`，不要等待主诊断内容。
5. 检查项目按 `priority` 排序展示。
6. `temporary_care` 仅用于就医前临时处置，不能作为治疗方案。
7. 始终展示 `warnings` 和接口原有 `disclaimer`。
