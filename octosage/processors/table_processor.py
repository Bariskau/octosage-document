from io import BytesIO
from .base import BaseProcessor
from ..types.models import TableElement
from docling_core.types.doc import TableItem, DoclingDocument


class TableProcessor(BaseProcessor):
    """
    Processor for table elements in a document.
    Extracts table data, converts to CSV format, and saves table image if available.
    """

    def process(self, element: TableItem, document: DoclingDocument) -> TableElement:
        """
        Process a table element from the document.

        Args:
            element: The table element to process
            document: The document containing the element

        Returns:
            TableElement: Processed table element with metadata, CSV data, and image path
        """
        metadata = self.get_base_metadata(element)
        # Convert table to pandas DataFrame
        table_df = element.export_to_dataframe()
        # Get table image if available
        image = element.get_image(document)

        path = None
        if image:
            # Convert image to bytes and save as PNG
            img_byte_arr = BytesIO()
            image.save(img_byte_arr, format="PNG")
            path = self.storage.save_file(img_byte_arr.getvalue(), self.get_filename(element, document))

        return TableElement(
            **metadata,
            captions=element.caption_text(document),
            data=table_df.to_csv(),
            path=path
        )
