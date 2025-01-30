from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    AcceleratorOptions,
    AcceleratorDevice,
)
from octosage.processors.manager import ProcessManager
from docling.datamodel.pipeline_options import (
    EasyOcrOptions,
)


class DocConverter:
    def __init__(self):
        self.process_manager = ProcessManager()

    def convert(self, source: str) -> list:
        """
        Convert a document and process its content

        Args:
            source: Path to the source document

        Returns:
            list: Processed document elements
        """
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.ocr_options = EasyOcrOptions(
            lang=["tr", "en"], force_full_page_ocr=True
        )
        pipeline_options.generate_picture_images = True
        pipeline_options.images_scale = 2.0
        pipeline_options.generate_table_images = True
        pipeline_options.accelerator_options = AcceleratorOptions(
            num_threads=4, device=AcceleratorDevice.CUDA
        )

        doc_converter = DocumentConverter(
            allowed_formats=[
                InputFormat.PDF,
                InputFormat.DOCX,
                InputFormat.PPTX,
            ],
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            },
        )

        # Convert document using docling
        result = doc_converter.convert(source)

        # Process the converted document
        return self.process_manager.process_document(result.document)
