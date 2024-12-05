from abc import ABC, abstractmethod


class BaseStorage(ABC):
    @abstractmethod
    def save_file(self, content: bytes, extension: str) -> str:
        """
        Save file content and return file path/identifier
        """
        pass

    @abstractmethod
    def get_file(self, file_path: str) -> bytes:
        """
        Retrieve file content by path/identifier
        """
        pass
