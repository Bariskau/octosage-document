class TransformOperation:
    def __init__(self, data):
        self.data = data
        self.elements = data["elements"]
        self.filename = data["metadata"]["filename"]
        self.hash = data["metadata"]["hash"]
        self.current_page_header = ""
        self.current_title = ""
        self.result = []
        self.current_section = ""
        self.text_buffer = []
        self.buffer_length = 0
        self.text_buffer_page = None

    def get_page_header(self, page_num, current_index):
        """Find page header for specific page"""
        # İlgili sayfadaki ilk 5 elemanı bul
        page_elements = []
        i = current_index
        while i < len(self.elements) and len(page_elements) < 5:
            if self.elements[i]["page"] == page_num:
                page_elements.append(self.elements[i])
            elif self.elements[i]["page"] > page_num:
                break
            i += 1

        # Öncelik sırasına göre kontrol et
        for elem in page_elements:
            if elem["label"] == "page_header":
                return elem["content"]
        for elem in page_elements:
            if elem["label"] == "title":
                return elem["content"]
        for elem in page_elements:
            if elem["label"] == "section_header":
                return elem["content"]

        return self.current_page_header  # Eğer bulunamazsa önceki header'ı koru

    def process_checkbox(self, element):
        """Process checkbox elements"""
        status = "selected" if element["label"] == "checkbox_selected" else "unselected"
        return f"Checkbox: {element['content']}: {status}"

    def get_surrounding_text(self, index, max_chars=500):
        """Get text before and after an element within same page"""
        before_text = []
        after_text = []
        current_page = self.elements[index]["page"]

        # Get text before
        i = index - 1
        chars_count = 0
        while i >= 0 and chars_count < max_chars:
            elem = self.elements[i]
            if elem["page"] != current_page:
                break
            if elem["label"] not in ["picture", "table", "formula"]:
                content = elem["content"]
                chars_count += len(content)
                if chars_count <= max_chars:
                    before_text.insert(0, content)
            i -= 1

        # Get text after
        i = index + 1
        chars_count = 0
        while i < len(self.elements) and chars_count < max_chars:
            elem = self.elements[i]
            if elem["page"] != current_page:
                break
            if elem["label"] not in ["picture", "table", "formula"]:
                content = elem["content"]
                chars_count += len(content)
                if chars_count <= max_chars:
                    after_text.append(content)
            i += 1

        return " ".join(before_text), " ".join(after_text)

    def flush_buffer(self):
        """Flush the current text buffer to results"""
        if self.text_buffer:
            content = " ".join(text for text in self.text_buffer)
            if content.strip():
                self.result.append(
                    {
                        "content": content,
                        "page": self.text_buffer_page,
                        "media_src": None,
                        "data": None,
                        "page_header": self.current_page_header,
                        "title": self.current_title,
                        "type": "text",
                    }
                )
            self.text_buffer = []
            self.buffer_length = 0
            self.text_buffer_page = None

    def process_special_element(self, element, index):
        """Process picture, table, or formula elements"""
        before_text, after_text = self.get_surrounding_text(index)
        content = []

        if before_text:
            content.append(before_text)

        if "captions" in element:
            content.append(element["captions"])

        if after_text:
            content.append(after_text)

        return {
            "content": "\n".join(content),
            "page": element["page"],
            "media_src": element.get("path"),
            "data": element.get("data"),
            "page_header": self.current_page_header,
            "title": self.current_title,
            "type": element["label"],
        }

    def should_create_new_element(self, element, content, is_section_header=False):
        """Check if we should create a new element"""
        if not self.text_buffer:
            return False

        # Sayfa değişiminde her zaman yeni eleman
        if self.text_buffer_page != element["page"]:
            return True

        if is_section_header:
            # Section header kontrolü
            return self.buffer_length + len(content) > 2000
        else:
            # Normal içerik kontrolü
            return self.buffer_length + len(content) > 2000

    def transform(self):
        """Transform the document data according to requirements"""
        current_page = None
        i = 0

        while i < len(self.elements):
            element = self.elements[i]

            # Sayfa değişimi kontrolü
            if current_page != element["page"]:
                self.flush_buffer()
                current_page = element["page"]
                self.current_page_header = self.get_page_header(current_page, i)

            # Special elements are always processed separately
            if element["label"] in ["picture", "table", "formula"]:
                self.flush_buffer()
                self.result.append(self.process_special_element(element, i))
                i += 1
                continue

            # Process content based on element type
            if element["label"] in ["checkbox_selected", "checkbox_unselected"]:
                content = self.process_checkbox(element)
            else:
                content = element["content"]

            # Handle section headers
            if element["label"] == "section_header":
                if self.should_create_new_element(element, content, True):
                    self.flush_buffer()

                self.current_section = content
                if not self.text_buffer:
                    self.text_buffer_page = element["page"]
                self.text_buffer.append(content)
                self.buffer_length += len(content)

                # Look ahead for content under this section within same page
                next_section_idx = i + 1
                section_content_length = 0
                while next_section_idx < len(self.elements):
                    next_elem = self.elements[next_section_idx]
                    if (
                        next_elem["page"] != current_page
                        or next_elem["label"] == "section_header"
                    ):
                        break
                    if next_elem["label"] not in ["picture", "table", "formula"]:
                        section_content_length += len(next_elem["content"])
                    next_section_idx += 1

                # If section content won't fit, flush and start new
                if self.buffer_length + section_content_length > 2000:
                    self.flush_buffer()
                    self.text_buffer = [content]
                    self.buffer_length = len(content)
                    self.text_buffer_page = element["page"]

                i += 1
                continue

            # Handle regular content
            if (
                len(content) < 50
                and self.text_buffer
                and self.text_buffer_page == element["page"]
            ):
                self.text_buffer.append(content)
                self.buffer_length += len(content)
            else:
                if self.should_create_new_element(element, content):
                    self.flush_buffer()

                if not self.text_buffer:
                    self.text_buffer_page = element["page"]
                self.text_buffer.append(content)
                self.buffer_length += len(content)

            i += 1

        # Flush any remaining content
        self.flush_buffer()

        return {
            "metadata": {
                "filename": self.filename,
                "hash": self.hash,
            },
            "elements": self.result,
        }
