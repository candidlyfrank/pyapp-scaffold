from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    service_name: str = "fastapi"
    title: str = "FastAPI Scaffold"
    version: str = "0.1.0"
    port: int = 8099


settings = Settings()
