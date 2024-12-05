from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Union


@dataclass
class BaseElement:
    label: str
    bbox: Optional[Tuple[float, float, float, float]]
    page: int
    type: str

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "page": self.page,
            "label": self.label,
            "bbox": self.bbox,
        }


@dataclass
class PictureElement(BaseElement):
    captions: Optional[str] = None  # varsayılan değer ekledim
    type: str = "picture"
    path: Optional[str] = None

    def to_dict(self) -> dict:
        return {**super().to_dict(), "captions": self.captions, "path": self.path}


@dataclass
class TableElement(BaseElement):
    data: str = None  # CSV formatted data
    captions: Optional[str] = None  # varsayılan değer ekledim
    type: str = "table"
    path: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "captions": self.captions,
            "data": self.data,
            "path": self.path,
        }


@dataclass
class TextElement(BaseElement):
    content: str = None
    type: str = "text"

    def to_dict(self) -> dict:
        return {**super().to_dict(), "content": self.content}


@dataclass
class GroupElement(BaseElement):
    elements: List[Union["GroupElement", TextElement, PictureElement, TableElement]] = (
        field(default_factory=list)
    )
    type: str = "group"

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "elements": [element.to_dict() for element in self.elements],
        }
