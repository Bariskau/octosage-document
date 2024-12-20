import json
import math
import random


def scale_bbox(bbox, original_width, original_height, target_size=1000):
    """Scale bbox coordinates to 1000x1000."""
    scale_factor_x = target_size / original_width
    scale_factor_y = target_size / original_height
    x1, y1, x2, y2 = bbox

    # Scale coordinates
    scaled_x1 = x1 * scale_factor_x
    scaled_x2 = x2 * scale_factor_x
    scaled_y1 = y1 * scale_factor_y
    scaled_y2 = y2 * scale_factor_y

    # Invert Y coordinates (1000 - y)
    inverted_y1 = target_size - scaled_y2
    inverted_y2 = target_size - scaled_y1

    return [scaled_x1, inverted_y1, scaled_x2, inverted_y2]


def split_box_into_segments(bbox, min_width=24, max_width=74, height=12, spacing=3):
    """Split a bounding box into segments with random widths"""
    x1, y1, x2, y2 = bbox
    box_width = x2 - x1
    box_height = y2 - y1

    segments = []
    current_row_y = y1

    while current_row_y + height <= y2:
        current_x = x1
        row_segments = []

        # Her satır için box'ları oluştur
        while current_x < x2:
            remaining_width = x2 - current_x

            if (
                remaining_width < min_width
            ):  # Kalan boşluk minimum genişlikten azsa, satırı bitir
                break

            # Random genişlik seç
            if remaining_width <= max_width:
                segment_width = remaining_width
            else:
                segment_width = random.randint(
                    min_width, min(max_width, remaining_width)
                )

            segment = [
                int(current_x),
                int(current_row_y),
                int(current_x + segment_width),
                int(current_row_y + height),
            ]

            row_segments.append(segment)
            current_x += segment_width + spacing

        segments.extend(row_segments)
        current_row_y += height + spacing

    return segments


def process_json(input_json):
    """Process the input JSON and add segmented boxes."""
    # Get original dimensions from metadata
    original_width = input_json["metadata"]["pages"]["1"]["width"]
    original_height = input_json["metadata"]["pages"]["1"]["height"]

    # Process each element
    processed_elements = []
    for element in input_json["elements"]:
        if "bbox" in element:
            # Scale the original bbox to 1000x1000 and invert Y coordinates
            scaled_bbox = scale_bbox(element["bbox"], original_width, original_height)

            # Split the scaled bbox into segments
            segments = split_box_into_segments(scaled_bbox)

            # Create new element with original and processed boxes
            new_element = element.copy()
            new_element["original_bbox"] = element["bbox"]
            new_element["scaled_bbox"] = scaled_bbox
            new_element["boxes"] = segments

            processed_elements.append(new_element)
        else:
            processed_elements.append(element)

    # Create output JSON
    output_json = input_json.copy()
    output_json["elements"] = processed_elements

    return output_json


# Example usage with your JSON data
def main():
    with open("a.json", "r", encoding="utf-8") as f:
        input_json = json.load(f)

    processed_json = process_json(input_json)

    # Save the processed JSON
    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(processed_json, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
