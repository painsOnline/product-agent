"""
文件名称：id_utils.py
作者：shop-tool
时间：2026-06-15
逻辑说明：ID 转换工具，将非 UUID 字符串转为确定性 UUID.
"""
import uuid

_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def str_to_uuid(s: str) -> uuid.UUID:
    try:
        return uuid.UUID(s)
    except (ValueError, AttributeError):
        return uuid.uuid5(_NAMESPACE, s)
