from pathlib import Path
from typing import Dict, Type, Optional, List, Union
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
from ..storage.base import BaseStorage
from ..storage.local import LocalStorage
from ..types.models import BaseElement
from ..settings import settings


class ProcessManager:
    def __init__(self, storage: Optional[BaseStorage] = None):
        self.storage = storage or LocalStorage(settings.OUTPUT_DIR)
        self.processors = {
            PictureItem: PictureProcessor(self.storage),
            TableItem: TableProcessor(self.storage),
            TextItem: TextProcessor(self.storage),
        }

    def process_element(
        self, element: DocItem, document: DoclingDocument
    ) -> Optional[Union[BaseElement, List[BaseElement]]]:
        """Process a single document element"""
        if isinstance(element, GroupItem):
            processed_elements = []
            # Extract the numeric ID from self_ref (e.g., '0' from '#/groups/0')
            group_id = element.self_ref.split("/")[-1]
            # Combine label and ID to form group_label_id (e.g., 'list_0')
            group_label_id = f"{element.label.value}/{group_id}"

            for child_ref in element.children:
                child_element = child_ref.resolve(document)
                processed_child = self.process_element(child_element, document)
                if processed_child:
                    # Add group_label_id to the processed child
                    setattr(processed_child, "group_id", group_label_id)
                    processed_elements.append(processed_child)

            return processed_elements

        for element_type, processor in self.processors.items():
            if isinstance(element, element_type):
                return processor.process(element, document)

        return None

    def get_page_metadata(self, document: DoclingDocument) -> Dict[int, dict]:
        """Extract page metadata from document"""
        metadata = {}
        for page_number, page in document.pages.items():
            metadata[page_number] = {
                "width": page.size.width,
                "height": page.size.height,
            }
        return metadata

    def process_document(self, document: DoclingDocument) -> dict:
        """Process entire document and convert to dictionary format with metadata"""
        elements = []

        for child_ref in document.body.children:
            element = child_ref.resolve(document)
            processed_element = self.process_element(element, document)
            if processed_element:
                if isinstance(processed_element, list):
                    # Handle group elements which return a list
                    elements.extend(element.to_dict() for element in processed_element)
                else:
                    # Handle single elements
                    elements.append(processed_element.to_dict())

        # Create final output with metadata
        return {
            "metadata": {"pages": self.get_page_metadata(document)},
            "elements": elements,
        }
