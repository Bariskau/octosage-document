from pathlib import Path
import uuid
from octosage.storage.base import BaseStorage


class LocalStorage(BaseStorage):
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path) if isinstance(base_path, str) else base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_file(self, content: bytes, filename: str) -> str:
        filename = self.base_path / filename
        with filename.open("wb") as fp:
            fp.write(content)
        return str(filename)

    def get_file(self, file_path: str) -> bytes:
        with open(file_path, "rb") as f:
            return f.read()
