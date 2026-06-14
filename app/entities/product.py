"""
文件名称：product.py
作者：shop-tool
时间：2026-06-14
逻辑说明：商品相关请求/响应实体定义.
"""
from pydantic import BaseModel, Field


class ProductSaveRequest(BaseModel):
    """商品保存请求."""
    ext_from: str = Field(..., description="来源平台：1688 / taobao")
    ext_product_id: str = Field(..., description="第三方商品唯一 ID")
    ext_product_name: str = Field(..., description="原始商品标题")
    main_picture: str = Field(..., description="主图外网 URL")
    pictures: list[str] = Field(..., description="轮播图 URL 数组")
    detail_pictures: list[str] = Field(
        default_factory=list, description="详情图 URL 数组"
    )
    attrs: dict[str, str] = Field(
        default_factory=dict, description="商品属性键值对"
    )


class ImageSuccessResult(BaseModel):
    """图片下载成功结果."""
    image_path: str = Field(..., description="服务器相对文件路径")
    image_size: int = Field(..., description="图片大小(字节)")
    is_main: bool | None = Field(None, description="是否主图(仅轮播图)")


class ImageFailResult(BaseModel):
    """图片下载失败结果."""
    image_name: str = Field(..., description="失败图片名称")
    reason: str = Field(..., description="失败原因")
    is_main: bool | None = Field(None, description="是否主图(仅轮播图)")


class SlideResult(BaseModel):
    """轮播图处理结果."""
    success_list: list[ImageSuccessResult] = Field(default_factory=list)
    fail_list: list[ImageFailResult] = Field(default_factory=list)


class DetailResult(BaseModel):
    """详情图处理结果."""
    success_list: list[ImageSuccessResult] = Field(default_factory=list)
    fail_list: list[ImageFailResult] = Field(default_factory=list)


class ProductSaveResponse(BaseModel):
    """商品保存响应."""
    id: str = Field(..., description="本地库主键 UUID")
    ext_from: str = Field(..., description="来源平台")
    ext_product_id: str = Field(..., description="外部商品ID")
    create_time: str = Field(..., description="创建时间")
    slide: SlideResult = Field(default_factory=SlideResult)
    detail: DetailResult = Field(default_factory=DetailResult)


class ProductGetRequest(BaseModel):
    """商品查询请求."""
    ext_from: str = Field(..., description="来源平台：1688 / taobao")
    ext_product_id: str = Field(..., description="第三方商品唯一 ID")


class ProductData(BaseModel):
    """商品详情数据."""
    id: str = Field(..., description="本地库主键 UUID")
    ext_from: str = Field(..., description="来源平台")
    ext_product_id: str = Field(..., description="外部商品ID")
    ext_product_name: str = Field(..., description="原始商品名称")
    main_picture: str = Field(..., description="主图路径")
    pictures: list[str] = Field(default_factory=list, description="轮播图路径")
    detail_pictures: list[str] = Field(
        default_factory=list, description="详情图路径"
    )
    attrs: dict[str, str] = Field(
        default_factory=dict, description="原始商品属性"
    )
