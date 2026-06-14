"""
文件名称：product_dto.py
作者：shop-tool
时间：2026-06-14
逻辑说明：商品保存响应 DTO 构建器，纯数据转换，无副作用.

从 product_service.py 中提取，遵循 SRP：编排与 DTO 组装分离.
"""
import uuid

from app.entities.product import (
    DetailResult,
    ImageFailResult,
    ImageSuccessResult,
    ProductSaveResponse,
    SlideResult,
)
from app.models.ext_product import ExtProductImportLog


def build_save_response(
    product: ExtProductImportLog,
    slides_success: list[dict],
    slides_fail: list[dict],
    details_success: list[dict],
    details_fail: list[dict],
) -> ProductSaveResponse:
    """根据下载结果和数据库记录构建响应 DTO.

    Args:
        product: 已保存的商品 ORM 实例
        slides_success: 轮播图下载成功列表
        slides_fail: 轮播图下载失败列表
        details_success: 详情图下载成功列表
        details_fail: 详情图下载失败列表

    Returns:
        ProductSaveResponse 完整响应对象
    """
    slide_success_result = [
        ImageSuccessResult(
            image_path=s["image_path"],
            image_size=s["image_size"],
            is_main=(idx == 0),
        )
        for idx, s in enumerate(slides_success)
    ]
    slide_fail_result = [
        ImageFailResult(image_name=f["image_name"], reason=f["reason"])
        for f in slides_fail
    ]

    detail_success_result = [
        ImageSuccessResult(
            image_path=d["image_path"],
            image_size=d["image_size"],
        )
        for d in details_success
    ]
    detail_fail_result = [
        ImageFailResult(image_name=d["image_name"], reason=d["reason"])
        for d in details_fail
    ]

    return ProductSaveResponse(
        id=str(product.id),
        ext_from=product.ext_from,
        ext_product_id=product.ext_product_id,
        create_time=product.create_time.strftime("%Y-%m-%d %H:%M:%S"),
        slide=SlideResult(
            success_list=slide_success_result,
            fail_list=slide_fail_result,
        ),
        detail=DetailResult(
            success_list=detail_success_result,
            fail_list=detail_fail_result,
        ),
    )
