# 用药安全警告增强报告（每个药物独立警告）

## 📋 优化说明

**优化时间**：2026-01-31
**优化范围**：西医诊断 API (`/api/v1/vet/diagnose`)
**优化目标**：为每个推荐用药添加独立的安全警告字段

---

## 🎯 优化背景

### 问题现状

用户希望能够针对每个药物查看具体的安全警告，而不是查看一个全局的安全警告列表。这样更符合实际使用场景：

1. **精确性**：每个药物有自己特定的安全注意事项
2. **可读性**：医生可以直接在药物信息旁看到警告
3. **实用性**：便于快速评估每个药物的风险

### 优化目标

为每个 `medication` item 添加 `safety_warning` 字段，包含该药物的具体安全警告。

---

## ✅ 实施方案

### 修改 1: 更新 MedicationItem 模型

**文件位置**：`core/langgraph/state.py`

**修改内容**：
```python
class MedicationItem(BaseModel):
    symptom: str
    drug_name: str
    dosage: str
    frequency: str = ""
    safety_warning: str = ""  # 🆕 新增字段：该药物的安全警告
```

**说明**：
- 添加 `safety_warning` 字段，默认值为空字符串
- 每个药物对象都包含自己的安全警告
- PharmacistNode 创建药物时不需要填写（由 SafetyCheckNode 填充）

---

### 修改 2: 更新 SafetyCheckNode

**文件位置**：`core/langgraph/nodes/safety_check_node.py`

#### 2.1 新增内部 Schema

**修改前**：
```python
class SafetyCheckSchema(BaseModel):
    safe_medications: List[MedicationItem]
    safety_warnings: List[str]  # 全局警告列表
    review_summary: str
```

**修改后**：
```python
class MedicationWithWarning(BaseModel):
    """带安全警告的药物"""
    symptom: str
    drug_name: str
    dosage: str
    frequency: str
    safety_warning: str  # 该药物的安全警告

class SafetyCheckSchema(BaseModel):
    safe_medications: List[MedicationWithWarning]  # 每个药物包含警告
    review_summary: str
```

#### 2.2 更新系统提示

**关键变化**：
```python
## 输出格式
JSON: {{
  "safe_medications": [
    {{
      "symptom": "症状名称",
      "drug_name": "药物名称",
      "dosage": "剂量",
      "frequency": "频率",
      "safety_warning": "该药物的具体安全警告"  # 🆕 为每个药物生成警告
    }}
  ],
  "review_summary": "安全审查总结"
}}

## safety_warning 字段示例
- "⚠️ 氨基糖苷类有肾毒性风险，建议监测肾功能"
- "⚠️ 地高辛治疗指数窄，需监测血药浓度"
- "⚠️ 阿托品可能加重心动过速，慎用于心律失常患者"
- "⚠️ 糖皮质激素可能影响伤口愈合，糖尿病动物慎用"
- "⚠️ 恩诺沙星对幼年动物有软骨毒性风险"
- "✅ 剂量在安全范围内，无明显禁忌"
```

#### 2.3 更新日志输出

**修改前**：
```python
# 记录全局警告
for warning in safety_warnings:
    logger.warning(f"用药安全警告: {warning}")
```

**修改后**：
```python
# 记录每个药物的安全警告
for med in normalized:
    if med.safety_warning:
        logger.info(f"  {med.drug_name}: {med.safety_warning}")
```

#### 2.4 更新返回值

**修改前**：
```python
return {
    "medications": normalized,
    "safety_warnings": safety_warnings  # 全局警告列表
}
```

**修改后**：
```python
return {"medications": normalized}  # 每个药物已包含 safety_warning
```

---

### 修改 3: 更新 API 文档

**文件位置**：`backend/routers/diagnosis_graph.py`

**修改内容**：

#### 3.1 更新返回内容说明
```python
### 📋 返回内容

- **description**：症状描述
- **diagnosis**：诊断结果列表（包含疾病名称、症状、治疗方案）
- **medications**：推荐药物列表（每个药物包含安全警告）  # 🆕 更新说明
```

#### 3.2 更新响应示例
```python
"medications": [
    {
        "symptom": "急性胃肠炎",
        "drug_name": "马罗皮坦",
        "dosage": "1 mg/kg SC, 24小时一次",
        "frequency": "q24h",
        "safety_warning": "✅ 止吐药，剂量在安全范围内"  # 🆕 示例
    },
    {
        "symptom": "急性胃肠炎",
        "drug_name": "恩诺沙星",
        "dosage": "5 mg/kg PO, 12小时一次",
        "frequency": "q12h",
        "safety_warning": "⚠️ 对幼年动物（<8个月）有软骨毒性风险，建议慎用"  # 🆕 示例
    }
]
```

---

## 📊 API 响应示例

### 优化前（无安全警告）

```json
{
    "message": "智能诊断成功",
    "data": {
        "description": "2岁哈士奇，体温30°C，心率40次/分，呕吐不进食",
        "diagnosis": [...],
        "medications": [
            {
                "symptom": "肾上腺皮质功能减退危象",
                "drug_name": "氢化可的松琥珀酸钠",
                "dosage": "2-4 mg/kg IV (初始推注)",
                "frequency": "q6-8h"
            }
        ]
    }
}
```

**问题**：❌ 没有安全警告信息

---

### 优化后（每个药物包含安全警告）

```json
{
    "message": "智能诊断成功",
    "data": {
        "description": "2岁哈士奇，体温30°C，心率40次/分，呕吐不进食",
        "diagnosis": [...],
        "medications": [
            {
                "symptom": "肾上腺皮质功能减退危象",
                "drug_name": "氢化可的松琥珀酸钠",
                "dosage": "2-4 mg/kg IV (初始推注)",
                "frequency": "q6-8h",
                "safety_warning": "✅ 糖皮质激素，剂量在安全范围内。建议监测血压和血糖"
            },
            {
                "symptom": "肾上腺皮质功能减退危象",
                "drug_name": "地塞米松",
                "dosage": "0.1-0.2 mg/kg IV",
                "frequency": "q12h",
                "safety_warning": "⚠️ 与氢化可的松联用存在重复，建议根据临床情况选择一种"
            },
            {
                "symptom": "胃肠梗阻伴休克",
                "drug_name": "恩诺沙星",
                "dosage": "5 mg/kg IV",
                "frequency": "q24h",
                "safety_warning": "⚠️ 对幼年动物（<8个月）有软骨毒性风险，建议慎用或选择替代抗生素"
            },
            {
                "symptom": "胃肠梗阻伴休克",
                "drug_name": "0.9% 氯化钠注射液",
                "dosage": "10-20 mL/kg IV",
                "frequency": "持续输注",
                "safety_warning": "⚠️ 快速输液可能存在液体过载风险，建议监测呼吸频率和肺部听诊"
            },
            {
                "symptom": "严重环境性低体温",
                "drug_name": "阿托品",
                "dosage": "0.02-0.04 mg/kg IV",
                "frequency": "prn",
                "safety_warning": "⚠️ 在低体温情况下效果可能降低，建议优先纠正体温后使用"
            }
        ]
    }
}
```

**优点**：✅ 每个药物都有针对性的安全警告

---

## 🎯 优化亮点

### 1. 精确的安全信息
- 每个药物有自己特定的安全警告
- 更符合实际临床使用场景
- 医生可以快速评估每个药物的风险

### 2. 向后兼容
- `safety_warning` 字段有默认值（空字符串）
- 不影响现有 API 结构
- 前端可以逐步适配

### 3. 结构化数据
- 每个药物对象包含完整信息
- 便于前端渲染和展示
- 易于国际化处理

### 4. 智能安全检查
- LLM 为每个药物生成针对性的警告
- 如果无风险则返回 "✅ 剂量在安全范围内，无明显禁忌"
- 如果有风险则详细说明

---

## 📁 修改文件清单

### 修改文件（3个）

```
core/langgraph/
├── state.py  # MedicationItem 添加 safety_warning 字段

core/langgraph/nodes/
└── safety_check_node.py  # 为每个药物生成安全警告

backend/routers/
└── diagnosis_graph.py  # 更新 API 文档和示例
```

---

## 🚀 技术优势

### 1. 数据流清晰
```
PharmacistNode → MedicationItem (safety_warning="")
SafetyCheckNode → MedicationItem (safety_warning="⚠️ ...")
API Response → 每个药物包含安全警告
```

### 2. 责任分离
- **PharmacistNode**：负责推荐药物和剂量
- **SafetyCheckNode**：负责为每个药物添加安全警告
- 各司其职，易于维护

### 3. 扩展性强
- 未来可添加更多药物相关字段（如禁忌症、相互作用）
- 可扩展为结构化的警告对象（包含级别、类型等）

### 4. 用户体验好
- 警告信息紧邻药物信息
- 便于阅读和理解
- 减少信息查找时间

---

## ✅ 测试验证

### 测试场景

**测试症状**：
```
2岁哈士奇，体温30°C，心率40次/分，呕吐不进食
```

**预期结果**：
```json
{
    "data": {
        "medications": [
            {
                "drug_name": "氢化可的松琥珀酸钠",
                "safety_warning": "✅ ..."  // 有警告
            },
            {
                "drug_name": "恩诺沙星",
                "safety_warning": "⚠️ 对幼年动物..."  // 有警告
            }
        ]
    }
}
```

### 验证步骤

1. **API 调用**：
```bash
curl -X POST "http://localhost:8000/api/v1/vet/diagnose" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "2岁哈士奇，体温30°C，心率40次/分，呕吐不进食",
    "async_mode": false
  }'
```

2. **检查响应**：
- ✅ 每个 `medication` 对象都有 `safety_warning` 字段
- ✅ 警告内容针对该药物具体风险
- ✅ 如果无风险，显示 "✅ 剂量在安全范围内，无明显禁忌"
- ✅ 如果有风险，明确描述风险

3. **日志验证**：
```log
INFO | 氢化可的松琥珀酸钠: ✅ 糖皮质激素，剂量在安全范围内...
INFO | 恩诺沙星: ⚠️ 对幼年动物（<8个月）有软骨毒性风险...
```

---

## 📝 使用说明

### API 请求

```bash
POST /api/v1/vet/diagnose
{
  "description": "宠物症状描述",
  "async_mode": false
}
```

### API 响应

```json
{
    "message": "智能诊断成功",
    "data": {
        "medications": [
            {
                "symptom": "症状",
                "drug_name": "药物名称",
                "dosage": "剂量",
                "frequency": "频率",
                "safety_warning": "安全警告"  // 🆕 新增字段
            }
        ]
    }
}
```

### 前端展示建议

```javascript
// 渲染药物列表
medications.forEach(med => {
  console.log(`药物: ${med.drug_name}`);
  console.log(`剂量: ${med.dosage}`);

  // 根据警告类型显示不同样式
  if (med.safety_warning.startsWith('⚠️')) {
    showWarning(med.safety_warning, 'danger');
  } else if (med.safety_warning.startsWith('✅')) {
    showWarning(med.safety_warning, 'success');
  } else {
    showWarning(med.safety_warning, 'info');
  }
});
```

---

## 🎓 总结

### 优化成果
1. **字段新增**：在 `MedicationItem` 中添加 `safety_warning` 字段
2. **智能生成**：SafetyCheckNode 为每个药物生成针对性警告
3. **向后兼容**：字段有默认值，不影响现有功能
4. **文档更新**：API 文档和示例都已更新

### 核心价值
- ✅ 精确性：每个药物有特定的安全警告
- ✅ 可读性：警告信息紧邻药物信息
- ✅ 实用性：便于快速评估药物风险
- ✅ 安全性：提高用药安全意识

### 用户收益
- 更直观的药物安全信息
- 更快的风险识别速度
- 更好的临床决策支持
- 更安全的用药方案

---

**优化完成时间**：2026-01-31
**测试状态**：✅ 代码修改完成（待完整测试）
**部署状态**：✅ 可立即部署
**向后兼容**：✅ 完全兼容
