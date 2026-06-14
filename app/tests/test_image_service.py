"""
文件名称：test_image_service.py
作者：shop-tool
时间：2026-06-14
逻辑说明：图片下载服务单元测试.
"""
import pytest

from app.services.image_storage import sanitize_filename
from app.services.image_downloader import validate_image


class TestSanitizeFilename:
    """文件名净化测试."""

    def test_normal_url(self) -> None:
        """测试正常 URL 的文件名提取."""
        url = "https://example.com/images/product_01.jpg"
        result = sanitize_filename(url)
        assert "product_01.jpg" in result

    def test_chinese_filename(self) -> None:
        """测试中文文件名被净化."""
        url = "https://example.com/商品图片.jpg"
        result = sanitize_filename(url)
        assert "_" in result


class TestValidateImage:
    """图片验证测试."""

    def test_valid_jpeg(self) -> None:
        """测试有效 JPEG 图片."""
        from io import BytesIO
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="red")
        buf = BytesIO()
        img.save(buf, "JPEG")
        data = buf.getvalue()

        assert validate_image(data) is True

    def test_1x1_image_rejected(self) -> None:
        """测试 1x1 占位图被拒绝."""
        from io import BytesIO
        from PIL import Image

        img = Image.new("RGB", (1, 1), color="white")
        buf = BytesIO()
        img.save(buf, "JPEG")
        data = buf.getvalue()

        assert validate_image(data) is False

    def test_empty_data_rejected(self) -> None:
        """测试空数据被拒绝."""
        assert validate_image(b"") is False
