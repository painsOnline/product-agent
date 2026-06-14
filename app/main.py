"""
文件名称：main.py
作者：shop-tool
时间：2026-06-14
逻辑说明：FastAPI 应用入口，注册路由、启动服务.
"""
import logging

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.api.upload_api import router as upload_router
from app.conf.settings import get_settings
from app.services.auth_service import AuthError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Product Agent API",
    description="商品导入与编辑 Agent 系统",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AuthError)
async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
    """全局 AuthError 异常处理器，将 AuthError.code 正确映射为 HTTP 响应."""
    return JSONResponse(
        status_code=int(exc.code) if exc.code.isdigit() else 500,
        content={
            "code": exc.code,
            "msg": exc.msg,
            "result": None,
        },
    )


app.include_router(upload_router)
app.include_router(api_router)


def main() -> None:
    """启动 Uvicorn 服务."""
    settings = get_settings()
    logger.info("Starting Product Agent API on %s:%s, upload_path=%s",
                settings.server_host, settings.server_port, settings.upload_path)
    uvicorn.run(
        "app.main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=True,
    )


if __name__ == "__main__":
    main()
