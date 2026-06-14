"""
文件名称：router.py
作者：shop-tool
时间：2026-06-14
逻辑说明：FastAPI 主路由，以 /agent/ 为前缀.
"""
from fastapi import APIRouter

from app.api.product_api import router as product_router
from app.api.chat_api import router as chat_router

api_router = APIRouter(prefix="/agent")

api_router.include_router(product_router)
api_router.include_router(chat_router)
