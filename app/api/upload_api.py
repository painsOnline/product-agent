"""
文件名称：upload_api.py
作者：shop-tool
时间：2026-06-14
逻辑说明：商品图片浏览接口，无鉴权，直接返回上传目录下的图片文件.
"""
import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from app.conf.settings import get_settings

router = APIRouter(tags=["uploads"])

settings = get_settings()


@router.get("/uploads/{file_path:path}")
async def serve_upload(file_path: str):
    """浏览商品图片.

    根据相对路径返回已上传的图片文件，无鉴权.
    """
    upload_root = Path(settings.upload_path).resolve()
    file = (upload_root / file_path).resolve()

    # 安全检查：确保文件在 upload_root 内
    if not str(file).startswith(str(upload_root)):
        return JSONResponse(
            status_code=404,
            content={"code": "404", "msg": "文件不存在", "result": None},
        )

    if not file.is_file():
        return JSONResponse(
            status_code=404,
            content={"code": "404", "msg": "文件不存在", "result": None},
        )

    content_type, _ = mimetypes.guess_type(str(file))
    return FileResponse(str(file), media_type=content_type or "application/octet-stream")
