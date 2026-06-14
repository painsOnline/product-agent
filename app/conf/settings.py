"""
文件名称：settings.py
作者：shop-tool
时间：2026-06-14
逻辑说明：全局配置管理，基于 pydantic-settings 从 .env 和环境变量加载配置.
"""
from pathlib import Path

from pydantic_settings import BaseSettings

_PROJECT_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """全局应用配置."""

    # Database
    db_host: str = "127.0.0.1"
    db_port: int = 1800
    db_user: str = "postgres"
    db_password: str = "mypg123abc"
    config_db: str = "mypet_config"

    # Redis
    redis_host: str = "127.0.0.1"
    redis_port: int = 6379
    redis_db: int = 6
    redis_password: str = ""

    # JWT
    jwt_secret: str = "mypet-jwt-secret-key-2026-minimum-32chars!!"
    jwt_expiration: int = 86400

    # Upload
    upload_path: str = "./uploads"

    # LLM defaults
    llm_provider: str = "deepseek"
    llm_model_name: str = "deepseek-chat"
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_api_key: str = ""
    llm_temperature: float = 0.3
    llm_max_tokens: int = 4096
    llm_timeout_seconds: int = 60
    llm_max_retries: int = 3

    # Agent
    agent_lock_timeout: int = 60
    agent_lock_wait_timeout: int = 60
    hitl_timeout: int = 600
    checkpoint_ttl: int = 3600

    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8083

    @property
    def db_url_config(self) -> str:
        """配置库连接字符串."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.config_db}"
        )

    @property
    def db_url_template(self) -> str:
        """租户库连接字符串模板，使用 {tenant_code} 占位."""
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/mypet_{{tenant_code}}"
        )

    @property
    def redis_url(self) -> str:
        """Redis 连接字符串."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    model_config = {
        "env_file": str(_PROJECT_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


def get_settings() -> Settings:
    """获取全局配置单例."""
    return Settings()
