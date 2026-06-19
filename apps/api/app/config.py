import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_FILE)


@dataclass(frozen=True)
class Settings:
    deepseek_api_key: str
    deepseek_model: str
    deepseek_base_url: str


def load_settings() -> Settings:
    api_key = os.getenv("DEEPSEEK_API_KEY")

    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured.")

    return Settings(
        deepseek_api_key=api_key,
        deepseek_model=os.getenv(
            "DEEPSEEK_MODEL",
            "deepseek-v4-flash",
        ),
        deepseek_base_url=os.getenv(
            "DEEPSEEK_BASE_URL",
            "https://api.deepseek.com",
        ),
    )


settings = load_settings()