"""Format the herb graph state into the API's existing list contract."""

import json
from typing import Any, Dict, List


def _as_dict(value: Any) -> Dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return value if isinstance(value, dict) else {}


def format_herb_result(final_state: Any) -> List[Dict[str, Any]]:
    state = (
        final_state.model_dump()
        if hasattr(final_state, "model_dump")
        else final_state if isinstance(final_state, dict) else vars(final_state)
    )
    zhengming = state.get("zhengming", [])
    prescriptions = state.get("prescriptions", [])
    nursing = state.get("nursing", [])

    if isinstance(zhengming, str):
        try:
            zhengming = json.loads(zhengming)
        except (json.JSONDecodeError, TypeError):
            zhengming = []

    nursing_by_category = {
        item.get("category", ""): item.get("content", "")
        for item in map(_as_dict, nursing)
    }
    base_nursing = nursing_by_category.get(
        "base", "饮食清淡易消化，保持环境温暖，适当运动"
    )
    continue_nursing = nursing_by_category.get("continue", "观察症状变化，监测精神状态")
    suggest_nursing = nursing_by_category.get("suggest", "持续呕吐腹泻或高热应立即就医")
    prescription_dicts = [_as_dict(item) for item in prescriptions]

    result = []
    for raw_item in zhengming:
        item = _as_dict(raw_item)
        name = item.get("zhengming", "")
        if not name:
            continue
        related = [
            prescription
            for prescription in prescription_dicts
            if prescription.get("zhengming")
            and (
                prescription["zhengming"] == name
                or name in prescription["zhengming"]
                or prescription["zhengming"] in name
            )
        ]
        by_type = {
            prescription.get("prescription_type", ""): prescription
            for prescription in related
        }
        base = by_type.get("基础方", {})
        continued = by_type.get("加减方", {})
        suggested = by_type.get("急救方", {})
        result.append(
            {
                "zhengming": name,
                "description": item.get("description", ""),
                "p": float(item.get("probability", 0.0)),
                "therapy": item.get("therapy", ""),
                "base": str(base_nursing) if base_nursing else "",
                "continue": str(continue_nursing) if continue_nursing else "",
                "suggest": str(suggest_nursing) if suggest_nursing else "",
                "base_prescription": base.get("prescription_name", ""),
                "base_prescription_usage": base.get("usage", ""),
                "continue_prescription": continued.get("prescription_name", ""),
                "continue_prescription_usage": continued.get("usage", ""),
                "suggest_prescription": suggested.get("prescription_name", ""),
                "suggest_prescription_usage": suggested.get("usage", ""),
            }
        )
    return result
