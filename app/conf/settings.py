"""
文件名称：settings.py
作者：shop-tool
时间：2026-06-14
逻辑说明：Spring Boot 风格多环境配置管理.

配置文件层级（后者覆盖前者）：
  1. .env              全局基础配置
  2. .env.{app_env}    环境专属配置（.env.development / .env.production）
  3. 系统环境变量        最高优先级

指定运行环境方式（优先级从高到低）：
  1. 系统环境变量 APP_ENV
  2. .env 文件中的 APP_ENV
  3. 代码默认值 "development"

注意：LLM 配置不在此处管理，统一从租户库 t_shop_llm_config 表读取.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_DIR = Path(__file__).resolve().parent.parent.parent

# ── 预加载配置文件到 os.environ（Spring Boot 风格）──
# Step 1: 加载 .env（基础配置）
load_dotenv(_PROJECT_DIR / ".env")

# Step 2: 确定运行环境（.env 中空值视为未设置，走默认值 development）
APP_ENV = os.getenv("APP_ENV") or "development"

# Step 3: 加载环境专属配置 .env.{APP_ENV}，覆盖 .env 空值
_env_profile = _PROJECT_DIR / f".env.{APP_ENV}"
if _env_profile.exists():
    load_dotenv(_env_profile, override=True)


class Settings(BaseSettings):
    """全局应用配置 — 所有可配置项的唯一入口."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
    )

    # ── 运行环境 ─────────────────────────────────
    app_env: str = "development"

    # ── PostgreSQL ───────────────────────────────
    db_host: str = "127.0.0.1"
    db_port: int = 1800
    db_user: str = "postgres"
    db_password: str = ""
    config_db: str = "mypet_config"

    # ── Redis ────────────────────────────────────
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 6
    redis_password: str = ""

    # ── JWT ──────────────────────────────────────
    jwt_secret: str = "change-me-in-production-minimum-32chars!!"
    jwt_expiration: int = 86400

    # ── 图片上传 ─────────────────────────────────
    upload_path: str = "./uploads"

    # ── Agent 执行 ───────────────────────────────
    agent_lock_timeout: int = 60
    agent_lock_wait_timeout: int = 60
    hitl_timeout: int = 600
    checkpoint_ttl: int = 3600

    # ── LangFuse ──────────────────────────────────
    langfuse_enabled: bool = False
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_base_url: str = "http://127.0.0.1:3000"

    # ── 服务 ─────────────────────────────────────
    server_host: str = "0.0.0.0"
    server_port: int = 8083

    # ── 便捷属性 ─────────────────────────────────

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def db_url_config(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.config_db}"
        )

    @property
    def db_url_template(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/mypet_{{tenant_code}}"
        )

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


def get_settings() -> Settings:
    """获取全局配置实例."""
    return Settings()
