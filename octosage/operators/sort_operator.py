import json
import math
import random
from transformers import LayoutLMv3ForTokenClassification
from helpers import prepare_inputs, boxes2inputs, parse_logits


class SortOperator:
    def __init__(self, target_width=1000, target_height=1000, line_height=16):
        self.target_width = target_width
        self.target_height = target_height
        self.line_height = line_height
        self.model = LayoutLMv3ForTokenClassification.from_pretrained(
            "hantian/layoutreader"
        )

        self.width_thresholds = [
            (800, 12),
            (500, 8),
            (300, 6),
            (150, 4),
            (0, 2),
        ]

    def scale_bbox(self, bbox, original_width, original_height):
        scale_x = self.target_width / original_width
        scale_y = self.target_height / original_height

        scaled_bbox = [
            min(self.target_width, max(0, bbox[0] * scale_x)),
            min(self.target_height, max(0, bbox[1] * scale_y)),
            min(self.target_width, max(0, bbox[2] * scale_x)),
            min(self.target_height, max(0, bbox[3] * scale_y)),
        ]

        if scaled_bbox[2] <= scaled_bbox[0]:
            scaled_bbox[2] = scaled_bbox[0] + 1
        if scaled_bbox[3] <= scaled_bbox[1]:
            scaled_bbox[3] = scaled_bbox[1] + 1

        return scaled_bbox

    def normalize_boxes(self, boxes):
        normalized_boxes = []
        for box in boxes:
            normalized_box = [
                min(self.target_width, max(0, box[0])),
                min(self.target_height, max(0, box[1])),
                min(self.target_width, max(0, box[2])),
                min(self.target_height, max(0, box[3])),
            ]

            if normalized_box[2] <= normalized_box[0]:
                normalized_box[2] = normalized_box[0] + 1
            if normalized_box[3] <= normalized_box[1]:
                normalized_box[3] = normalized_box[1] + 1

            normalized_boxes.append(normalized_box)
        return normalized_boxes

    def get_width_splits(self, width):
        for threshold, splits in self.width_thresholds:
            if width > threshold:
                return splits
        return 1

    def split_bbox(self, bbox):
        x1, y1, x2, y2 = bbox
        width = x2 - x1
        height = y2 - y1

        num_height_splits = max(1, math.ceil(height / self.line_height))
        height_step = height / num_height_splits

        num_width_splits = self.get_width_splits(width)
        width_step = width / num_width_splits

        split_boxes = []
        current_y = y1

        for i in range(num_height_splits):
            current_x = x1
            y_gap = 2 if i < num_height_splits - 1 else 0
            row_height = min(height_step - y_gap, y2 - current_y)

            for j in range(num_width_splits):
                x_gap = random.uniform(2, 8) if j < num_width_splits - 1 else 0
                box_width = min(width_step - x_gap, x2 - current_x)

                new_box = [
                    int(current_x),
                    int(current_y),
                    int(current_x + box_width),
                    int(current_y + row_height),
                ]
                split_boxes.append(new_box)
                current_x += box_width + x_gap

            current_y += row_height + y_gap

        return self.normalize_boxes(split_boxes)

    def process_json(self, input_data):
        original_width = input_data["metadata"]["pages"]["1"]["width"]
        original_height = input_data["metadata"]["pages"]["1"]["height"]

        result = input_data.copy()

        all_elements = []
        all_boxes = []
        box_to_element_map = {}
        current_box_index = 0

        # Process elements
        for element in result["elements"]:
            if element["type"] == "group" and "elements" in element:
                # Önce grup içindeki elementleri işle
                sub_boxes = []
                for sub_element in element["elements"]:
                    if "bbox" in sub_element:
                        scaled_sub_bbox = self.scale_bbox(
                            sub_element["bbox"], original_width, original_height
                        )
                        sub_element["bbox"] = scaled_sub_bbox
                        sub_element["boxes"] = self.split_bbox(scaled_sub_bbox)
                        # Alt elemanların box'larını grup için topla
                        sub_boxes.extend(sub_element["boxes"])

                # Grubun boxes'larını alt elemanlardan al
                if "bbox" in element:
                    scaled_group_bbox = self.scale_bbox(
                        element["bbox"], original_width, original_height
                    )
                    element["bbox"] = scaled_group_bbox
                    element["boxes"] = sub_boxes

                # Grup elementini listeye ekle ve box'ları kaydet
                for box in element["boxes"]:
                    all_boxes.append(box)
                    box_to_element_map[current_box_index] = element
                    current_box_index += 1

                all_elements.append(element)

            elif "bbox" in element:
                # Normal elementleri işle
                scaled_bbox = self.scale_bbox(
                    element["bbox"], original_width, original_height
                )
                element["bbox"] = scaled_bbox
                element["boxes"] = self.split_bbox(scaled_bbox)

                for box in element["boxes"]:
                    all_boxes.append(box)
                    box_to_element_map[current_box_index] = element
                    current_box_index += 1

                all_elements.append(element)

        if all_boxes:
            all_boxes = self.normalize_boxes(all_boxes)
            print(f"Total boxes: {len(all_boxes)}")

            inputs = boxes2inputs(all_boxes)
            inputs = prepare_inputs(inputs, self.model)
            logits = self.model(**inputs).logits.cpu().squeeze(0)
            orders = parse_logits(logits, len(all_boxes))

            # Her element için order belirle
            for element in all_elements:
                element_boxes_indices = [
                    i for i, box in enumerate(all_boxes) if box in element["boxes"]
                ]
                if element_boxes_indices:
                    element["order"] = min(orders[i] for i in element_boxes_indices)
                else:
                    element["order"] = float("inf")

            # Elementleri sırala
            sorted_elements = sorted(
                all_elements, key=lambda x: x.get("order", float("inf"))
            )
            result["elements"] = sorted_elements

        return result


if __name__ == "__main__":
    with open("././a.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    sorter = SortOperator()
    processed_data = sorter.process_json(data)

    with open("processed.json", "w", encoding="utf-8") as f:
        json.dump(processed_data, f, indent=2, ensure_ascii=False)
