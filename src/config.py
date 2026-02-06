"""
ClawBots Configuration

Environment-aware configuration for development and production.
"""

import os
from typing import Optional
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass
class DatabaseConfig:
    """Database configuration."""
    url: str = "sqlite:///clawbots.db"
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    echo: bool = False


@dataclass
class RedisConfig:
    """Redis configuration."""
    url: str = "redis://localhost:6379/0"
    max_connections: int = 50
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0


@dataclass
class OpenSimConfig:
    """OpenSim configuration."""
    enabled: bool = False
    grid_url: str = "http://localhost:9000"
    admin_url: str = "http://localhost:9000"
    admin_password: str = ""
    default_region: str = "Bhairav"
    auto_spawn: bool = True


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    enabled: bool = True
    registration_limit: int = 5  # per hour
    connection_limit: int = 10   # per minute
    action_limit: int = 60       # per minute
    websocket_limit: int = 100   # per minute


@dataclass
class Config:
    """
    Main configuration class.
    
    Loads from environment variables with sensible defaults.
    """
    # Environment
    env: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    
    # API
    api_prefix: str = "/api/v1"
    cors_origins: list = field(default_factory=lambda: ["*"])
    
    # Components
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    opensim: OpenSimConfig = field(default_factory=OpenSimConfig)
    rate_limit: RateLimitConfig = field(default_factory=RateLimitConfig)
    
    # World
    tick_rate: float = 1.0  # seconds
    max_agents_per_region: int = 100
    event_history_size: int = 1000
    
    # Features
    enable_spectator: bool = True
    enable_opensim: bool = False
    enable_metrics: bool = True
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        env = os.getenv("CLAWBOTS_ENV", "development")
        
        # Database
        db_url = os.getenv("DATABASE_URL", "sqlite:///clawbots.db")
        if env == "production" and "sqlite" in db_url:
            raise ValueError("SQLite not allowed in production!")
        
        database = DatabaseConfig(
            url=db_url,
            pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
            echo=os.getenv("DB_ECHO", "false").lower() == "true"
        )
        
        # Redis
        redis = RedisConfig(
            url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))
        )
        
        # OpenSim
        opensim = OpenSimConfig(
            enabled=os.getenv("OPENSIM_ENABLED", "false").lower() == "true",
            grid_url=os.getenv("OPENSIM_GRID_URL", "http://localhost:9000"),
            admin_url=os.getenv("OPENSIM_ADMIN_URL", "http://localhost:9000"),
            admin_password=os.getenv("OPENSIM_ADMIN_PASSWORD", ""),
            default_region=os.getenv("OPENSIM_DEFAULT_REGION", "Bhairav"),
            auto_spawn=os.getenv("OPENSIM_AUTO_SPAWN", "true").lower() == "true"
        )
        
        # Rate limits
        rate_limit = RateLimitConfig(
            enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
            registration_limit=int(os.getenv("RATE_LIMIT_REGISTER", "5")),
            connection_limit=int(os.getenv("RATE_LIMIT_CONNECT", "10")),
            action_limit=int(os.getenv("RATE_LIMIT_ACTION", "60"))
        )
        
        return cls(
            env=env,
            debug=os.getenv("DEBUG", "false").lower() == "true",
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            host=os.getenv("HOST", "0.0.0.0"),
            port=int(os.getenv("PORT", "8000")),
            workers=int(os.getenv("WORKERS", "1")),
            database=database,
            redis=redis,
            opensim=opensim,
            rate_limit=rate_limit,
            enable_opensim=opensim.enabled,
            enable_metrics=os.getenv("ENABLE_METRICS", "true").lower() == "true"
        )
    
    @property
    def is_production(self) -> bool:
        return self.env == "production"
    
    @property
    def is_development(self) -> bool:
        return self.env == "development"


@lru_cache()
def get_config() -> Config:
    """Get cached configuration instance."""
    return Config.from_env()


# Convenience function
config = get_config
