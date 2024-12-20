import json
import cv2
import numpy as np
import random


def generate_random_color():
    """Rastgele BGR renk üret"""
    return (
        random.randint(0, 255),  # B
        random.randint(0, 255),  # G
        random.randint(0, 255),  # R
    )


def draw_boxes(data):
    """JSON'daki boxları görselleştir"""
    # 1000x1000 beyaz bir görüntü oluştur
    image = np.ones((1000, 1000, 3), dtype=np.uint8) * 255

    # Tüm boxları topla
    all_boxes = []
    for element in data["elements"]:
        if "boxes" in element:
            for box in element["boxes"]:
                all_boxes.append(
                    {
                        "box": box,
                        "y": 1000 - box[1],  # ters çevrilmiş y koordinatı
                        "content": element.get("content", "")[:30],
                    }
                )

    # Boxları y koordinatına göre sırala
    all_boxes.sort(key=lambda x: x["y"], reverse=True)

    # Her box için farklı bir renk tonu kullan
    total_boxes = len(all_boxes)

    for i, box_data in enumerate(all_boxes):
        box = box_data["box"]

        # Kırmızıdan maviye doğru bir renk gradyanı
        intensity = int(255 * (i / total_boxes))
        color = (intensity, 0, 255 - intensity)  # BGR format

        # Box'ı çiz
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 1)

        # Sıra numarasını yaz
        cv2.putText(
            image, str(i), (x1, y1 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.3, color, 1
        )

    # Debug için y koordinatlarını yazdır
    print(f"İlk 5 box'ın orijinal ve çevrilmiş y koordinatları:")
    for i, box_data in enumerate(all_boxes[:5]):
        print(f"Box {i}: y = {box_data['y']}")

    # Görüntüyü kaydet
    cv2.imwrite("boxes_sorted_flipped.png", image)

    # Görüntüyü göster
    cv2.imshow("Sorted Boxes (Flipped)", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def main():
    with open("output.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    # JSON dosyasından okuma ve görselleştirme
    draw_boxes(data)


if __name__ == "__main__":
    main()
