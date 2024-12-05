import torch
import os
from dotenv import find_dotenv
from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    OUTPUT_DIR: str = os.path.join(BASE_DIR, "output")
    DEVICE: str = "cuda:0" if torch.cuda.is_available() else "cpu"

    class Config:
        env_file = find_dotenv("local.env")
        extra = "ignore"


settings = Settings()
