from io import BytesIO
from .base import BaseProcessor
from ..types.models import PictureElement
from docling_core.types.doc import PictureItem, DoclingDocument


class PictureProcessor(BaseProcessor):
    """
    Processor for picture elements in a document.
    Extracts image data, saves it to storage, and processes captions.
    """

    def process(
        self, element: PictureItem, document: DoclingDocument
    ) -> PictureElement:
        """
        Process a picture element from the document.

        Args:
            element: The picture element to process
            document: The document containing the element

        Returns:
            PictureElement: Processed picture element with metadata, captions, and image path
        """
        metadata = self.get_base_metadata(element)
        # Get image data from the element
        image = element.get_image(document)

        path = None
        if image:
            # Convert image to bytes and save as PNG
            img_byte_arr = BytesIO()
            image.save(img_byte_arr, format="PNG")
            path = self.storage.save_file(
                img_byte_arr.getvalue(), self.get_filename(element, document)
            )

        return PictureElement(
            **metadata, captions=element.caption_text(document), path=path
        )
