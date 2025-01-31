from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import blue
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
from reportlab.lib.colors import blue, red, green, purple, orange, HexColor


class PDFDrawingService:
    def __init__(self):
        # Register font for multi-language support
        self.font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        pdfmetrics.registerFont(TTFont("DejaVuSans", self.font_path))

        # Define colors for each element type
        self.type_colors = {
            "text": blue,
            "picture": green,
            "section_header": purple,
            "list_item": orange,
            "table": red,
        }

        # Font size settings
        self.font_size = 6  # Reduced from 8
        self.box_height = 8  # Reduced from 12

    def draw_text_box(self, canvas, text, x, y, width=None, bg_color=blue):
        """Draw text with a colored background box"""
        can = canvas
        padding = 1  # Reduced from 2
        text_width = can.stringWidth(text, "DejaVuSans", self.font_size)
        if width is None:
            width = text_width + 2 * padding

        # Draw background box
        can.setFillColor(bg_color)
        can.setStrokeColor(bg_color)
        can.rect(x, y - 1, width, self.box_height, stroke=1, fill=1)  # Height reduced

        # Draw text in white color
        can.setFillColor(HexColor("#FFFFFF"))
        can.drawString(x + padding, y, text)

    def draw_annotations(self, pdf_path: str, elements: list) -> bytes:
        """Draw annotations on PDF with element boxes and information"""
        reader = PdfReader(pdf_path)
        writer = PdfWriter()

        for page_num in range(len(reader.pages)):
            page = reader.pages[page_num]
            page_width = float(page.mediabox.width)
            page_height = float(page.mediabox.height)

            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=(page_width, page_height))
            can.setFont("DejaVuSans", self.font_size)  # Use smaller font size

            page_elements = [e for e in elements if e.get("page") == page_num + 1]

            for idx, element in enumerate(page_elements, 1):
                bbox = element["bbox"]
                element_type = element.get("type", "text")

                left = bbox[0]
                right = bbox[2]
                top = bbox[1]
                bottom = bbox[3]

                # Draw main box with semi-transparent fill
                box_color = self.type_colors.get(element_type, blue)
                can.setStrokeColor(box_color)
                box_height = bottom - top

                fill_color = self.type_colors.get(element_type, blue)
                can.setFillColor(fill_color)
                can.setFillAlpha(0.3)
                can.rect(left, top, right - left, box_height, stroke=1, fill=1)
                can.setFillAlpha(1)

                # Adjust text box positions
                text_y_offset = self.box_height + 1  # Reduced offset

                # Top left: Type info
                type_text = f"Type: {element_type}"
                self.draw_text_box(
                    can, type_text, left, top - text_y_offset, None, box_color
                )

                # Top right: Order number
                order_text = f"Order: {idx}"
                order_width = (
                    can.stringWidth(order_text, "DejaVuSans", self.font_size) + 2
                )
                self.draw_text_box(
                    can,
                    order_text,
                    right - order_width,
                    top - text_y_offset,
                    None,
                    box_color,
                )

                # Bottom left: Label info
                label_text = f"Label: {element.get('label', 'N/A')}"
                self.draw_text_box(can, label_text, left, bottom + 2, None, box_color)

                # Bottom right: Group ID info
                group_text = f"Group ID: {element.get('group_id', 'N/A')}"
                group_width = (
                    can.stringWidth(group_text, "DejaVuSans", self.font_size) + 2
                )
                self.draw_text_box(
                    can, group_text, right - group_width, bottom + 2, None, box_color
                )

            can.save()
            packet.seek(0)

            new_pdf = PdfReader(packet)
            page.merge_page(new_pdf.pages[0])
            writer.add_page(page)

        output_buffer = io.BytesIO()
        writer.write(output_buffer)
        output_buffer.seek(0)

        return output_buffer.getvalue()
