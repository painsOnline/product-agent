"""
文件名称：main.py
作者：shop-tool
时间：2026-06-14
逻辑说明：FastAPI 应用入口，注册路由、启动服务.
"""
import logging
import os
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.api.upload_api import router as upload_router
from app.conf.settings import get_settings
from app.core.langfuse_client import init_langfuse, shutdown_langfuse
# 启动时显式初始化 LangFuse
print("[main DEBUG] Calling init_langfuse()...")
init_langfuse()
print("[main DEBUG] init_langfuse() returned")
from app.services.auth_service import AuthError


def _setup_logging() -> None:
    """配置日志：控制台 + 文件滚动（50MB，logs/YYYYMMDD-N.log）."""
    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "logs"
    )
    os.makedirs(log_dir, exist_ok=True)

    today = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(log_dir, f"{today}.log")

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=50 * 1024 * 1024,
        backupCount=10,
        encoding="utf-8",
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    ))
    file_handler.namer = lambda name: re.sub(
        r"(.+)\.log\.(\d+)$", r"\1-\2.log", name
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    ))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(console_handler)


_setup_logging()
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
        reload=settings.is_development,
    )


if __name__ == "__main__":
    main()
