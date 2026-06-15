"""
文件名称：llm_service.py
作者：shop-tool
时间：2026-06-14
逻辑说明：LLM 调用服务，负责调用 DeepSeek 模型并解析结构化输出.

解析流程：
1. 调用 LLM 获取原始返回
2. 移除 markdown 包装、JSON 注释（// /* */）和多余话术
3. 使用 Pydantic Schema 校验（严格绑定 llm_schema.md 所有字段/类型/非空约束）
4. 解析失败记录日志，返回降级数据
"""
import json
import logging
import re
import time
from collections.abc import Callable
from typing import Any

from app.core.llm import create_llm
from app.conf.constants import ActionStatus, ActionType
from app.entities.agent_outputs import (
    AttributeMatcherOutput,
    SupervisorOutput,
    TitleOptimizerOutput,
)

logger = logging.getLogger(__name__)


def _strip_json_wrapper(raw: str) -> str:
    """移除 LLM 返回中的 markdown 代码块、JSON 注释和多余文字."""
    text = raw.strip()

    # 移除 markdown 代码块
    if "```json" in text:
        text = text.split("```json", 1)[1]
    elif "```" in text:
        text = text.split("```", 1)[1]
    if "```" in text:
        text = text.rsplit("```", 1)[0]

    # 移除单行注释 // ...
    text = re.sub(r"//[^\n]*", "", text)

    # 移除多行注释 /* ... */
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)

    text = text.strip()

    # 处理多余的尾部内容
    if text.startswith("{") and not text.endswith("}"):
        last_brace = text.rfind("}")
        if last_brace > 0:
            text = text[: last_brace + 1]

    return text


def parse_llm_json(raw_text: str) -> dict[str, Any]:
    """解析 LLM 返回的 JSON 字符串为字典."""
    cleaned = _strip_json_wrapper(raw_text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse LLM JSON: %s", e)
        logger.debug("Raw text: %s", raw_text[:500])
        raise


def validate_llm_output(
    parsed: dict[str, Any],
    operate_type: str,
) -> dict[str, Any]:
    """使用 Pydantic 模型校验 LLM 结构化输出.

    按 operate_type 选择对应 Schema 进行校验：
    - rewrite_title → TitleOptimizerOutput
    - match_attr → AttributeMatcherOutput
    - both → SupervisorOutput
    """
    if operate_type == "rewrite_title":
        model = TitleOptimizerOutput(**parsed)
    elif operate_type == "match_attr":
        model = AttributeMatcherOutput(**parsed)
    else:
        model = SupervisorOutput(**parsed)
    return model.model_dump()


async def call_llm_with_logging(
    prompt: str,
    user_id: str,
    import_product_id: str,
    operate_type: str = "both",
    llm_config: dict | None = None,
    log_callback: Callable | None = None,
) -> dict[str, Any]:
    """调用 LLM 并记录日志.

    统一使用 agent/llm.py::create_llm() 创建模型实例.
    """
    start_time = time.time()

    llm_raw_output = ""
    try:
        llm = create_llm(llm_config)

        response = await llm.ainvoke(prompt)
        llm_raw_output = (
            response.content if hasattr(response, "content") else str(response)
        )

        parsed = parse_llm_json(llm_raw_output)
        validated = validate_llm_output(parsed, operate_type)

        cost_ms = int((time.time() - start_time) * 1000)

        if log_callback:
            await log_callback(
                action_type=ActionType.LLM_INVOKE,
                status=ActionStatus.SUCCESS,
                request={"prompt": prompt},
                response={"raw": llm_raw_output, "parsed": validated},
                metadata={
                    "model_name": getattr(llm, "model_name", ""),
                    "cost_ms": cost_ms,
                },
            )

        return validated

    except Exception as e:
        cost_ms = int((time.time() - start_time) * 1000)
        is_timeout = "timeout" in str(e).lower()

        if log_callback:
            await log_callback(
                action_type=(
                    ActionType.LLM_TIMEOUT
                    if is_timeout
                    else ActionType.PARSE_ERROR
                ),
                status=ActionStatus.FAILURE,
                request={"prompt": prompt},
                response={"raw": llm_raw_output, "error": str(e)},
                metadata={
                    "cost_ms": cost_ms,
                    "error_msg": str(e),
                },
            )

        raise
