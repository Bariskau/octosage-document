from typing import List
from docling_core.types.doc import GroupItem, DoclingDocument, DocItem
from .base import BaseProcessor
from ..types.models import BaseElement, GroupElement


class GroupProcessor(BaseProcessor):
    def _calculate_metadata(self, elements: List[BaseElement]) -> dict:
        """Calculate bbox and page information from child elements"""
        if not elements:
            return {"bbox": None, "page": None}

        min_x = float("inf")
        min_y = float("inf")
        max_x = float("-inf")
        max_y = float("-inf")
        pages = set()

        def process_element_bbox(element: BaseElement):
            nonlocal min_x, min_y, max_x, max_y, pages

            if element.page is not None:
                pages.add(element.page)

            if element.bbox:
                x1, y1, x2, y2 = element.bbox
                min_x = min(min_x, x1)
                min_y = min(min_y, y1)
                max_x = max(max_x, x2)
                max_y = max(max_y, y2)

            if isinstance(element, GroupElement):
                for child in element.elements:
                    process_element_bbox(child)

        for element in elements:
            process_element_bbox(element)

        bbox = None
        if min_x != float("inf"):
            bbox = (min_x, min_y, max_x, max_y)

        page = min(pages) if pages else None

        return {"bbox": bbox, "page": page}

    def process(
        self, element: GroupItem, document: DoclingDocument, process_element_func
    ) -> GroupElement:
        """
        Process a group element and its children.

        Args:
            element: Group element to process
            document: Document containing the elements
            process_element_func: Function to process child elements
        """
        metadata = self.get_base_metadata(element)
        processed_group = GroupElement(**metadata, bbox=None, page=None)

        # Process children
        for child_ref in element.children:
            child_element = child_ref.resolve(document)
            processed_child = process_element_func(child_element, document)
            if processed_child:
                processed_group.elements.append(processed_child)

        # Update metadata from children
        if processed_group.elements:
            group_metadata = self._calculate_metadata(processed_group.elements)
            processed_group.bbox = group_metadata["bbox"]
            processed_group.page = group_metadata["page"]

        return processed_group

    def get_base_metadata(self, element: DocItem) -> dict:
        """Only get the label and type, let concrete processors handle bbox and page"""
        return {"label": element.label.value, "type": "group"}
