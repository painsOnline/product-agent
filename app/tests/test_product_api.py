"""
文件名称：test_product_api.py
作者：shop-tool
时间：2026-06-14
逻辑说明：商品 API 和实体模型单元测试.
"""
import pytest
from pydantic import ValidationError


class TestProductSaveRequest:
    """商品保存请求实体."""

    def test_valid_request(self) -> None:
        from app.entities.product import ProductSaveRequest
        req = ProductSaveRequest(
            ext_from="1688",
            ext_product_id="740960285767",
            ext_product_name="测试商品",
            main_picture="https://example.com/main.jpg",
            pictures=["https://example.com/slide1.jpg"],
            detail_pictures=[],
            attrs={"品牌": "测试品牌"},
        )
        assert req.ext_from == "1688"
        assert req.ext_product_id == "740960285767"

    def test_missing_required_fields(self) -> None:
        from app.entities.product import ProductSaveRequest
        with pytest.raises(ValidationError):
            ProductSaveRequest()

    def test_invalid_platform(self) -> None:
        from app.entities.product import ProductSaveRequest
        req = ProductSaveRequest(
            ext_from="jd",
            ext_product_id="123",
            ext_product_name="test",
            main_picture="",
            pictures=[],
            detail_pictures=[],
            attrs={},
        )
        assert req.ext_from == "jd"


class TestProductGetRequest:
    """商品查询请求实体."""

    def test_valid_request(self) -> None:
        from app.entities.product import ProductGetRequest
        req = ProductGetRequest(
            ext_from="1688",
            ext_product_id="740960285767",
        )
        assert req.ext_from == "1688"

    def test_missing_fields(self) -> None:
        from app.entities.product import ProductGetRequest
        with pytest.raises(ValidationError):
            ProductGetRequest()


class TestSupervisorOutput:
    """LLM 结构化输出实体."""

    def test_default_values(self) -> None:
        from app.entities.agent import SupervisorOutput
        output = SupervisorOutput()
        assert output.new_title == ""
        assert output.title_note == ""
        assert output.attr_mapping == []

    def test_full_output(self) -> None:
        from app.entities.agent import SupervisorOutput
        from app.entities.chat import AttrMapping
        output = SupervisorOutput(
            new_title="夏季纯棉T恤",
            title_note="已优化",
            import_product_id="p1",
            thread_id="t1",
            user_id="u1",
            attr_mapping=[
                AttrMapping(target_name="材质", target_value="纯棉",
                            source_name="面料", source_value="棉",
                            map_note="匹配"),
            ],
            warning={"has_warn": False, "warn_content": ""},
            suggestion={"summary": "无", "items": []},
        )
        assert output.new_title == "夏季纯棉T恤"
        assert len(output.attr_mapping) == 1
        assert output.attr_mapping[0].target_name == "材质"


class TestChatEntities:
    """聊天实体模型."""

    def test_attr_mapping(self) -> None:
        from app.entities.chat import AttrMapping
        m = AttrMapping(
            target_name="材质", target_value="纯棉",
            source_name="面料", source_value="棉",
        )
        assert m.map_note == ""

    def test_api_response_format(self) -> None:
        from app.entities.common import APIResponse
        r = APIResponse[dict](code="200", msg="ok", result={"a": 1})
        assert r.code == "200"
        assert r.result == {"a": 1}

    def test_paginated_response(self) -> None:
        from app.entities.common import PaginatedResponse, PaginatedResult
        r = PaginatedResponse[str]()
        assert r.code == "200"
        assert r.result.page == 1
