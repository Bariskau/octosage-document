from octosage.processors.base import BaseProcessor
from octosage.types.models import TextElement
from docling_core.types.doc import TextItem, DoclingDocument


class TextProcessor(BaseProcessor):
    """
    Processor for text elements in a document.
    Extracts text content from TextItem elements.
    """

    def process(self, element: TextItem, document: DoclingDocument) -> TextElement:
        """
        Process a text element from the document.

        Args:
            element: The text element to process
            document: The document containing the element

        Returns:
            TextElement: Processed text element with metadata and content
        """
        metadata = self.get_base_metadata(element)

        return TextElement(**metadata, content=element.text)
