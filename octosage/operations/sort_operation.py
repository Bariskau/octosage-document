import copy
from typing import List, Dict, Any
import torch
from octosage.utils.helpers import prepare_inputs, boxes2inputs, parse_logits
from collections import defaultdict
from transformers import LayoutLMv3ForTokenClassification
from octosage.settings import settings
from contextlib import ContextDecorator


class ModelManager(ContextDecorator):
    """Context manager for handling model lifecycle"""

    def __init__(self):
        self.model = None

    def __enter__(self):
        self.model = LayoutLMv3ForTokenClassification.from_pretrained(
            "hantian/layoutreader"
        )
        self.model.to(settings.DEVICE)
        return self.model

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.model is not None:
            self.model.cpu()  # Move model back to CPU
            del self.model  # Remove model reference
            if torch.cuda.is_available():
                torch.cuda.empty_cache()  # Clear CUDA cache
        return False  # Propagate exceptions if any


class SortOperation:
    def __init__(self):
        """Initialize without loading model"""
        self.model_manager = ModelManager()

    def sort(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Main processing pipeline for document sorting"""
        processed_data = self._preprocess_data(data)

        with self.model_manager as model:
            processed_data["elements"] = self._process_elements(processed_data, model)

        return processed_data

    def _preprocess_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Filter and prepare input data by removing unwanted elements"""
        processed_data = copy.deepcopy(data)
        processed_data["elements"] = [
            el
            for el in processed_data["elements"]
            if el["label"] not in ["page_footer", "caption"]
        ]
        return processed_data

    def _process_elements(
        self, data: Dict[str, Any], model: LayoutLMv3ForTokenClassification
    ) -> List[Dict]:
        """Process elements with page-wise grouping and sorting"""
        elements = []
        for element in data["elements"]:
            if "bbox" in element:
                page_num = element["page"]
                page_meta = data["metadata"]["pages"][page_num]
                element = self._process_element(element, page_meta)
            elements.append(element)

        # Group elements by page number
        page_groups = defaultdict(list)
        for element in elements:
            page_groups[element["page"]].append(element)

        # Process pages in numerical order
        sorted_elements = []
        for page_num in sorted(page_groups.keys()):
            page_elements = self._sort_elements(page_groups[page_num], model)
            sorted_elements.extend(page_elements)

        return sorted_elements

    def _process_element(self, element: Dict, page_meta: Dict) -> Dict:
        """Enhance element data with split bounding boxes"""
        original_width = page_meta["width"]
        original_height = page_meta["height"]
        element["boxes"] = self._split_bbox(
            element["bbox"], original_width, original_height
        )
        return element

    def _split_bbox(
        self,
        bbox: List[float],
        page_w: int,
        page_h: int,
        target_width: int = 1000,
        target_height: int = 1000,
    ) -> List[List[float]]:
        """Split bounding box into grid cells based on content analysis"""
        left, top, right, bottom = bbox
        block_width = right - left
        block_height = bottom - top

        # Calculate dynamic line height threshold
        line_height = max(page_h // 20, 30)

        # Handle small elements that don't need splitting
        if block_height < line_height * 2 and block_width < page_w * 0.4:
            return self._scale_bboxes(
                [[left, top, right, bottom]],
                page_w,
                page_h,
                target_width,
                target_height,
            )

        # Calculate row parameters
        min_rows = 2 if block_height > line_height * 3 else 1
        rows = max(min_rows, int(round(block_height / line_height)))
        row_height = block_height / rows

        # Determine column count
        cols = self._calculate_columns(block_width, page_w, block_height, page_h)

        # Generate grid cells
        boxes = []
        for row in range(rows):
            y_start = top + row * row_height
            y_end = bottom if row == rows - 1 else y_start + row_height

            for col in range(cols):
                col_width = block_width / cols
                x_start = left + col * col_width
                x_end = right if col == cols - 1 else x_start + col_width

                boxes.append([x_start, y_start, x_end, y_end])

        return self._scale_bboxes(boxes, page_w, page_h, target_width, target_height)

    def _calculate_columns(
        self, block_width: float, page_w: float, block_height: float, page_h: float
    ) -> int:
        """Determine optimal column count based on block dimensions"""
        if block_width > page_w * 0.6:
            return 3
        if block_width > page_w * 0.4:
            return 2
        if block_width > page_w * 0.25 and block_height / page_h < 0.2:
            return 2
        return 1

    def _scale_bboxes(
        self,
        boxes: List[List[float]],
        original_width: int,
        original_height: int,
        target_width: int = 1000,
        target_height: int = 1000,
    ) -> List[List[int]]:
        """Normalize bounding boxes to target dimensions"""
        scale_x = target_width / original_width
        scale_y = target_height / original_height
        scaled_boxes = []

        for box in boxes:
            x1 = round(box[0] * scale_x)
            y2 = target_height - round(box[1] * scale_y)
            x2 = round(box[2] * scale_x)
            y1 = target_height - round(box[3] * scale_y)
            scaled_boxes.append([int(i) for i in [x1, y1, x2, y2]])

        return scaled_boxes

    def _sort_elements(
        self, elements: List[Dict], model: LayoutLMv3ForTokenClassification
    ) -> List[Dict]:
        """Sort elements within a single page using model predictions"""
        flat_boxes = []
        element_indices = []
        box_counts = []

        # Create mapping between elements and their boxes
        for idx, element in enumerate(elements):
            boxes = element.get("boxes", [])
            box_counts.append(len(boxes))
            flat_boxes.extend(boxes)
            element_indices.extend([idx] * len(boxes))
            element["order_sum"] = 0

        if not flat_boxes:
            return elements

        # Get model predictions
        with torch.no_grad():
            inputs = boxes2inputs(flat_boxes)
            inputs = prepare_inputs(inputs, model)
            outputs = model(**inputs)
            logits = outputs.logits.cpu().squeeze(0)

        # Parse model output to get reading order
        orders = parse_logits(logits, len(flat_boxes))

        # Accumulate position scores for each element
        for pos, box_idx in enumerate(orders):
            element_idx = element_indices[box_idx]
            elements[element_idx]["order_sum"] += pos

        # Calculate average position for each element
        for idx, element in enumerate(elements):
            if box_counts[idx] > 0:
                element["orders"] = element["order_sum"] / box_counts[idx]
            else:
                element["orders"] = float("inf")
            del element["order_sum"]
            element.pop("boxes", None)

        # Return elements sorted by their average position
        return sorted(elements, key=lambda x: x["orders"])
