from pathlib import Path
from typing import Dict, Type, Optional, List
from docling_core.types.doc import (
    DoclingDocument,
    GroupItem,
    TableItem,
    PictureItem,
    TextItem,
    DocItem,
)
from .picture_processor import PictureProcessor
from .table_processor import TableProcessor
from .text_processor import TextProcessor
from .group_processor import GroupProcessor
from ..storage.base import BaseStorage
from ..storage.local import LocalStorage
from ..types.models import BaseElement, GroupElement
from ..settings import settings


class ProcessManager:
    def __init__(self, storage: Optional[BaseStorage] = None):
        self.storage = storage or LocalStorage(settings.OUTPUT_DIR)
        self.group_processor = GroupProcessor(self.storage)
        self.processors = {
            PictureItem: PictureProcessor(self.storage),
            TableItem: TableProcessor(self.storage),
            TextItem: TextProcessor(self.storage),
        }

    def process_element(
        self, element: DocItem, document: DoclingDocument
    ) -> Optional[BaseElement]:
        """Process a single document element"""
        if isinstance(element, GroupItem):
            return self.group_processor.process(
                element, document, process_element_func=self.process_element
            )

        for element_type, processor in self.processors.items():
            if isinstance(element, element_type):
                return processor.process(element, document)

        return None

    def process_document(self, document: DoclingDocument) -> List[dict]:
        """Process entire document and convert to dictionary format"""
        result = []

        for child_ref in document.body.children:
            element = child_ref.resolve(document)
            processed_element = self.process_element(element, document)
            if processed_element:
                result.append(processed_element.to_dict())

        return result
