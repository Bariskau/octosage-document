import json
from transformers import LayoutLMv3ForTokenClassification
from helpers import prepare_inputs, boxes2inputs, parse_logits
import torch


def extract_boxes_from_json(data):
    """JSON'dan boxes array'lerini çıkart"""
    all_boxes = []  # Tüm box'ları tutacak liste
    elements_with_boxes = []  # Box'ları olan elementler
    box_to_element_index = []  # Her box'ın element listesindeki index'i

    for element in data["elements"]:
        if "boxes" in element and element["boxes"]:
            current_index = len(elements_with_boxes)
            elements_with_boxes.append(element)

            for box in element["boxes"]:
                all_boxes.append(box)
                box_to_element_index.append(current_index)

    return all_boxes, elements_with_boxes, box_to_element_index


def sort_json(input_path, output_path):
    # JSON'ı yükle
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Box'ları ve elementleri çıkart
    boxes, elements_with_boxes, box_to_element_index = extract_boxes_from_json(data)

    print(f"Number of boxes: {len(boxes)}")
    print(f"Number of elements with boxes: {len(elements_with_boxes)}")

    if not boxes:
        print("No boxes found in JSON")
        return

    # Model yükle ve tahmin yap
    model = LayoutLMv3ForTokenClassification.from_pretrained("hantian/layoutreader")
    inputs = boxes2inputs(boxes)
    inputs = prepare_inputs(inputs, model)

    with torch.no_grad():
        logits = model(**inputs).logits.cpu().squeeze(0)

    # Box'ların sırasını al
    box_orders = parse_logits(logits, len(boxes))
    print(f"Box orders received: {len(box_orders)}")

    # Her element için en erken box pozisyonunu bul
    element_first_positions = {}
    for box_idx, element_idx in enumerate(box_to_element_index):
        box_position = box_orders[box_idx]
        if element_idx not in element_first_positions:
            element_first_positions[element_idx] = box_position
        else:
            element_first_positions[element_idx] = min(
                element_first_positions[element_idx], box_position
            )

    # Elementleri sırala
    element_order = sorted(
        range(len(elements_with_boxes)),
        key=lambda x: element_first_positions.get(x, float("inf")),
    )

    # Sıralanmış elementlerle yeni JSON oluştur
    sorted_elements = [elements_with_boxes[i] for i in element_order]

    # Boxes olmayan elementleri bul
    elements_without_boxes = [
        elem for elem in data["elements"] if "boxes" not in elem or not elem["boxes"]
    ]

    # Yeni JSON oluştur
    output_data = {"metadata": data["metadata"], "elements": []}

    # Önce sıralanmış elementleri ekle (boxes key'i olmadan)
    for element in sorted_elements:
        new_element = element.copy()
        if "boxes" in new_element:
            del new_element["boxes"]
        output_data["elements"].append(new_element)

    # Sonra boxes olmayan elementleri ekle
    output_data["elements"].extend(elements_without_boxes)

    # Sonucu kaydet
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"Processed {len(sorted_elements)} elements with boxes")
    print(f"Added {len(elements_without_boxes)} elements without boxes")
    print(f"Total elements in output: {len(output_data['elements'])}")


if __name__ == "__main__":
    sort_json("output.json", "sorted_output.json")
