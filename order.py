from transformers import LayoutLMv3ForTokenClassification
import torch
from collections import defaultdict
import copy
from typing import List, Dict, Optional
import json
from enum import Enum, auto


class BlockType(Enum):
    Text = auto()
    Picture = auto()
    Group = auto()
    Title = auto()
    InterlineEquation = auto()
    ImageCaption = auto()
    ImageFootnote = auto()
    TableCaption = auto()
    TableFootnote = auto()
    ImageBody = auto()
    TableBody = auto()


def insert_lines_into_block(block_bbox, line_height, page_w, page_h):
    x0, y0, x1, y1 = block_bbox

    block_height = y1 - y0
    block_weight = x1 - x0

    if line_height * 3 < block_height:
        if block_height > page_h * 0.25 and page_w * 0.5 > block_weight > page_w * 0.25:
            lines = int(block_height / line_height) + 1
        else:
            if block_weight > page_w * 0.4:
                line_height = (y1 - y0) / 3
                lines = 3
            elif block_weight > page_w * 0.25:
                lines = int(block_height / line_height) + 1
            else:
                if block_height / block_weight > 1.2:
                    return [[x0, y0, x1, y1]]
                else:
                    line_height = (y1 - y0) / 2
                    lines = 2

        current_y = y0
        lines_positions = []

        for i in range(lines):
            lines_positions.append([x0, current_y, x1, current_y + line_height])
            current_y += line_height
        return lines_positions
    else:
        return [[x0, y0, x1, y1]]


def prepare_model_inputs(boxes: List[List[float]]) -> Dict[str, torch.Tensor]:
    bbox = [[0, 0, 0, 0]] + boxes + [[0, 0, 0, 0]]
    input_ids = [0] + [3] * len(boxes) + [2]  # CLS, UNK, EOS tokens
    attention_mask = [1] + [1] * len(boxes) + [1]
    return {
        "bbox": torch.tensor([bbox], dtype=torch.long),
        "attention_mask": torch.tensor([attention_mask], dtype=torch.long),
        "input_ids": torch.tensor([input_ids], dtype=torch.long),
    }


def sort_blocks_by_model(
    blocks: List[dict], page_w: float, page_h: float, line_height: float
) -> Optional[List[List[float]]]:
    # Satırları topla
    page_line_list = []
    processed_blocks = []

    for block in blocks:
        block_type = block["type"].lower()
        bbox = block["bbox"]

        if block_type == "text":
            if "elements" in block:  # Grup içindeki metinler için
                for element in block["elements"]:
                    if element["type"] == "text":
                        page_line_list.append(element["bbox"])
            else:
                page_line_list.append(bbox)

        elif block_type == "group":
            if "elements" in block:
                for element in block["elements"]:
                    if element["type"] == "text":
                        page_line_list.append(element["bbox"])

        elif block_type in ["picture"]:
            lines = insert_lines_into_block(bbox, line_height, page_w, page_h)
            page_line_list.extend(lines)

    if len(page_line_list) > 200:  # layoutreader limit
        return None

    # Koordinatları 1000x1000 ölçeğine normalize et
    x_scale = 1000.0 / page_w
    y_scale = 1000.0 / page_h
    normalized_boxes = []

    for left, top, right, bottom in page_line_list:
        # Sınırları kontrol et
        left = max(0, min(left, page_w))
        right = max(0, min(right, page_w))
        top = max(0, min(top, page_h))
        bottom = max(0, min(bottom, page_h))

        # Normalize et
        scaled_box = [
            round(left * x_scale),
            round(top * y_scale),
            round(right * x_scale),
            round(bottom * y_scale),
        ]

        if not (
            1000 >= scaled_box[2] >= scaled_box[0] >= 0
            and 1000 >= scaled_box[3] >= scaled_box[1] >= 0
        ):
            print(f"Invalid box coordinates: {scaled_box}")
            continue

        normalized_boxes.append(scaled_box)

    try:
        # Model yükle ve tahmin yap
        model = LayoutLMv3ForTokenClassification.from_pretrained("hantian/layoutreader")
        inputs = prepare_model_inputs(normalized_boxes)

        for k, v in inputs.items():
            v = v.to(model.device)
            if torch.is_floating_point(v):
                v = v.to(model.dtype)

        with torch.no_grad():
            logits = model(**inputs).logits.cpu().squeeze(0)
            logits = logits[1 : len(normalized_boxes) + 1, : len(normalized_boxes)]
            orders = logits.argsort(descending=False).tolist()
            final_orders = [o.pop() for o in orders]

        # Sıralanmış orijinal kutuları döndür
        sorted_bboxes = [page_line_list[i] for i in final_orders]
        return sorted_bboxes

    except Exception as e:
        print(f"Model tahmin hatası: {str(e)}")
        return None


# Kullanım örneği
def process_document(json_data, page_width=1000, page_height=1000, line_height=20):
    blocks = json.loads(json_data) if isinstance(json_data, str) else json_data
    sorted_lines = sort_blocks_by_model(blocks, page_width, page_height, line_height)
    return sorted_lines


print(
    process_document(
        """[
  {
    "type": "text",
    "page": 1,
    "label": "section_header",
    "bbox": [
      101.56500244140625,
      753.4412231445312,
      510.6809997558594,
      769.1055297851562
    ],
    "content": "4.4 Kablo / Malzeme Baca \u00f7 \u00d5 Haz \u00d5 rlama, Kalaylama (Devam \u00d5 )"
  },
  {
    "type": "text",
    "page": 1,
    "label": "caption",
    "bbox": [
      77.59918212890625,
      608.8346557617188,
      138.06678771972656,
      622.22216796875
    ],
    "content": "Resim 4-4"
  },
  {
    "type": "picture",
    "page": 1,
    "label": "picture",
    "bbox": [
      69.90550994873047,
      629.721435546875,
      267.50506591796875,
      727.0975952148438
    ],
    "captions": "Resim 4-4",
    "path": "/home/qzer/Desktop/work/document/output/media-d28270d2-ab1b-47d9-b05d-dd7baf02f3c7.png"
  },
  {
    "type": "text",
    "page": 1,
    "label": "caption",
    "bbox": [
      95.0544662475586,
      176.68112182617188,
      155.1610870361328,
      190.06866455078125
    ],
    "content": "Resim 4-5"
  },
  {
    "type": "picture",
    "page": 1,
    "label": "picture",
    "bbox": [
      69.79855346679688,
      198.16644287109375,
      249.6786346435547,
      286.74481201171875
    ],
    "captions": "Resim 4-5",
    "path": "/home/qzer/Desktop/work/document/output/media-971fdf7a-ccc2-433f-a738-618fb641f378.png"
  },
  {
    "type": "text",
    "page": 1,
    "label": "page_footer",
    "bbox": [
      70.58727264404297,
      49.2578010559082,
      167.9326629638672,
      61.50735092163086
    ],
    "content": "IPC-WHMA-A-620B"
  },
  {
    "type": "text",
    "page": 1,
    "label": "page_footer",
    "bbox": [
      267.5823059082031,
      49.2578010559082,
      329.9461364746094,
      61.50735092163086
    ],
    "content": "Kas \u00d5 m 2012"
  },
  {
    "type": "text",
    "page": 1,
    "label": "page_footer",
    "bbox": [
      501.1040344238281,
      49.2578010559082,
      527.3121337890625,
      61.50735092163086
    ],
    "content": "4-11"
  },
  {
    "type": "text",
    "page": 1,
    "label": "section_header",
    "bbox": [
      292.3149719238281,
      683.27099609375,
      441.0149841308594,
      724.2493286132812
    ],
    "content": "Kabul edilir-S \u00d5 n \u00d5 f 1 Proses \u00f8 ndikat\u00f6r\u00fc-S \u00d5 n \u00d5 f 2 Kusur-S \u00d5 n \u00d5 f 3"
  },
  {
    "type": "group",
    "page": 1,
    "label": "list",
    "bbox": [
      293.9000549316406,
      572.4210205078125,
      530.4464721679688,
      669.127685546875
    ],
    "elements": [
      {
        "type": "text",
        "page": 1,
        "label": "list_item",
        "bbox": [
          293.9673156738281,
          613.8905029296875,
          530.4464721679688,
          669.127685546875
        ],
        "content": "\u00b7 Kalaylanm \u00d5 \u00fa kablo \u00fczerinde k\u00fc\u00e7\u00fck delikler, bo \u00fa luklar, kalaylanmas \u00d5 gereken alan \u00d5 n %5'ini ge\u00e7en iyi yap \u00d5 \u00fa mama veya hi\u00e7 yap \u00d5 \u00fa mama durumlar \u00d5 ."
      },
      {
        "type": "text",
        "page": 1,
        "label": "list_item",
        "bbox": [
          293.9000549316406,
          572.4210205078125,
          528.8941040039062,
          613.9448852539062
        ],
        "content": "\u00b7 Kalaylanm \u00d5 \u00fa k \u00d5 s \u00d5 m ile izolasyon aras \u00d5 ndaki kalaylanmam \u00d5 \u00fa k \u00d5 sm \u00d5 n uzunlu \u00f7 unun 1 kablo \u00e7ap \u00d5 ndan (D) daha fazla olmas \u00d5 ."
      }
    ]
  },
  {
    "type": "text",
    "page": 1,
    "label": "text",
    "bbox": [
      293.6953125,
      490.18939208984375,
      522.5770263671875,
      558.7609252929688
    ],
    "content": "Not: J-STD-002 (Malzeme bacaklar \u00d5 , sonland \u00d5 rmalar, terminaller ve kablolar i\u00e7in lehimlenebilirlik testleri) bu gerekliliklerin uygulanmas \u00d5 i\u00e7in ek bilgiler ihtiva etmektedir."
  },
  {
    "type": "text",
    "page": 1,
    "label": "section_header",
    "bbox": [
      295.5071716308594,
      421.1523742675781,
      387.3760986328125,
      434.5399169921875
    ],
    "content": "Kusur-S \u00d5 n \u00d5 f 2,3"
  },
  {
    "type": "group",
    "page": 1,
    "label": "list",
    "bbox": [
      296.20733642578125,
      337.7318420410156,
      533.6228637695312,
      407.0079040527344
    ],
    "elements": [
      {
        "type": "text",
        "page": 1,
        "label": "list_item",
        "bbox": [
          296.20733642578125,
          379.824951171875,
          484.2449645996094,
          407.0079040527344
        ],
        "content": "\u00b7 Kalaylanan b\u00f6l\u00fcmde iyi yap \u00d5 \u00fa ma olmamas \u00d5 ."
      },
      {
        "type": "text",
        "page": 1,
        "label": "list_item",
        "bbox": [
          296.6087646484375,
          337.7318420410156,
          533.6228637695312,
          379.4237976074219
        ],
        "content": "\u00b7 Damarl \u00d5 kablolar \u00d5 n terminallere montaj \u00d5 ndan \u00f6nce ve kablo eklemelerinde (a \u00f7 metodu hari\u00e7) kalaylanmamas \u00d5"
      }
    ]
  },
  {
    "type": "text",
    "page": 1,
    "label": "section_header",
    "bbox": [
      286.2071533203125,
      264.8500061035156,
      388.07061767578125,
      278.237548828125
    ],
    "content": "Kusur-S \u00d5 n \u00d5 f 1,2,3"
  },
  {
    "type": "group",
    "page": 1,
    "label": "list",
    "bbox": [
      283.0820007324219,
      124.49443817138672,
      512.2664184570312,
      251.06661987304688
    ],
    "elements": [
      {
        "type": "text",
        "page": 1,
        "label": "list_item",
        "bbox": [
          283.1243591308594,
          207.75128173828125,
          511.6954345703125,
          251.06661987304688
        ],
        "content": "x Kablonun kullan \u00d5 l \u00d5 r b\u00f6l\u00fcm\u00fcnde, sonraki ad \u00d5 mlar \u00d5 etkileyecek \u00fa ekilde lehim y \u00d5 \u00f7 \u00d5 lmas \u00d5 veya sa\u00e7ak olu \u00fa mas \u00d5 ."
      },
      {
        "type": "text",
        "page": 1,
        "label": "list_item",
        "bbox": [
          283.11419677734375,
          166.72035217285156,
          498.33673095703125,
          208.83950805664062
        ],
        "content": "x Bi\u00e7im, uygunluk ve fonksiyonu etkileyecek \u00fa ekilde yo \u00f7 un kalaylama olmas \u00d5 ."
      },
      {
        "type": "text",
        "page": 1,
        "label": "list_item",
        "bbox": [
          283.0820007324219,
          124.49443817138672,
          512.2664184570312,
          166.67237854003906
        ],
        "content": "x Lehimlemeden sonra kablonun esnek kalmas \u00d5 gereken k \u00d5 s \u00d5 mlar \u00d5 na lehim ak \u00d5 \u00fa \u00d5 olmas \u00d5"
      }
    ]
  }
]"""
    )
)
