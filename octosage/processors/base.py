from abc import ABC, abstractmethod
from docling_core.types.doc import DocItem, DoclingDocument
from octosage.types.models import BaseElement
from octosage.storage.base import BaseStorage


class BaseProcessor(ABC):
    def __init__(self, storage: BaseStorage):
        self.storage = storage

    @abstractmethod
    def process(self, element: DocItem, document: DoclingDocument) -> BaseElement:
        pass

    def get_base_metadata(self, element: DocItem) -> dict:
        return {
            "label": element.label.value,
            "bbox": (
                element.prov[0].bbox.as_tuple()
                if hasattr(element, "prov") and element.prov
                else None
            ),
            "page": (
                element.prov[0].page_no
                if hasattr(element, "prov") and element.prov
                else None
            ),
        }

    def get_filename(self, element: DocItem, document: DoclingDocument) -> BaseElement:
        filename = "_".join(element.self_ref.split("/")[1:]) + ".png"
        return f"{document.origin.binary_hash}_{filename}"
