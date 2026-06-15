"""
文件名称：product_api.py
作者：shop-tool
时间：2026-06-14
逻辑说明：商品数据管理 API 接口.

接口：
- POST /agent/product/save — 保存第三方商品数据
- GET /agent/product/get — 查询商品数据
- POST /agent/product/auto-match — Agent 自动匹配标题和属性
"""
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.entities.product import AutoMatchRequest, ProductSaveRequest
from app.conf.constants import StatusCode
from app.core.context import RequestContext
from app.services import auto_match_service, product_service
from app.services.auth_service import AuthError
from app.utils.response_utils import error, success

logger = logging.getLogger(__name__)

router = APIRouter(tags=["商品管理"])


@router.post(
    "/product/save",
    summary="保存第三方商品数据",
    description="插件抓取商品标题、属性、图片地址后，调用该接口存入数据库，并按租户+商品ID生成图片存储目录",
)
async def save_product(
    req: ProductSaveRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """保存商品数据，下载图片到本地."""
    try:
        result = await product_service.save_product(
            db=db,
            tenant_code=user["tenant_code"],
            ext_from=req.ext_from,
            ext_product_id=req.ext_product_id,
            ext_product_name=req.ext_product_name,
            main_picture_url=req.main_picture,
            pictures_urls=req.pictures,
            detail_pictures_urls=req.detail_pictures,
            attrs=req.attrs,
        )
        await db.commit()
        return success(result.model_dump(), msg="保存成功")
    except AuthError:
        raise
    except Exception as e:
        logger.exception("Failed to save product")
        await db.rollback()
        return error(code=StatusCode.SERVER_ERROR, msg=str(e))


@router.get(
    "/product/get",
    summary="查询商品数据",
    description="根据平台类型和第三方商品ID查询已保存的商品数据",
)
async def get_product(
    ext_from: str = Query(..., description="来源平台：1688 / taobao"),
    ext_product_id: str = Query(..., description="第三方商品唯一 ID"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查询商品详情."""
    try:
        product = await product_service.get_product(
            db, ext_from, ext_product_id
        )
        if not product:
            return error(
                code=StatusCode.NOT_FOUND,
                msg=f"商品未找到: {ext_from}/{ext_product_id}",
            )
        return success(product.model_dump())
    except AuthError:
        raise
    except Exception as e:
        logger.exception("Failed to get product")
        return error(code="500", msg=str(e))


@router.post(
    "/product/auto-match",
    summary="Agent 自动匹配标题和属性",
    description="根据已保存的商品数据，由 Agent 自动优化标题并匹配属性，无需对话",
)
async def auto_match_product(
    req: AutoMatchRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Agent 自动匹配."""
    try:
        ctx = RequestContext(
            tenant_code=user["tenant_code"],
            user_id=user["user_id"],
            import_product_id=req.ext_product_id,
        )
        ctx.thread_id = f"{user['user_id']}_{req.ext_product_id}"
        ctx.activate()
        await ctx.init_tenant_db()

        target_attrs = [
            t.model_dump() for t in req.target_attrs
        ] if req.target_attrs else None
        result = await auto_match_service.auto_match(
            ctx, req.ext_from, req.ext_product_id, target_attrs=target_attrs
        )

        await db.commit()
        await ctx.close()
        return success(result)
    except ValueError as e:
        return error(code=StatusCode.NOT_FOUND, msg=str(e))
    except Exception as e:
        logger.exception("Auto-match failed")
        await db.rollback()
        return error(code=StatusCode.SERVER_ERROR, msg=str(e))
