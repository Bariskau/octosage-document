from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.backend.docling_parse_v2_backend import DoclingParseV2DocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    AcceleratorOptions,
    AcceleratorDevice,
    EasyOcrOptions,
)
from octosage.processors.manager import ProcessManager
from typing import List
from octosage.settings import settings


class DocConverter:
    def __init__(
        self,
        languages: List[str] = ["tr", "en"],
        force_full_page_ocr: bool = True,
        images_scale: float = 2.0,
        num_threads: int = 4,
    ):
        """
        Initialize the document converter with customizable parameters.

        Args:
            languages: List of language codes for OCR
            force_full_page_ocr: Whether to force full page OCR
            images_scale: Scale factor for generated images
            num_threads: Number of threads for processing
        """
        self.languages = languages
        self.force_full_page_ocr = force_full_page_ocr
        self.images_scale = images_scale
        self.num_threads = num_threads
        self.process_manager = ProcessManager()

    def convert(self, source: str) -> list:
        """
        Convert a document and process its content

        Args:
            source: Path to the source document

        Returns:
            list: Processed document elements
        """

        # Determine the device based on settings
        if settings.DEVICE.startswith("cuda"):
            device = AcceleratorDevice.CUDA
        else:
            device = AcceleratorDevice.CPU

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True
        pipeline_options.ocr_options = EasyOcrOptions(
            lang=self.languages,
            force_full_page_ocr=self.force_full_page_ocr,
        )

        pipeline_options.generate_picture_images = True
        pipeline_options.images_scale = self.images_scale
        pipeline_options.generate_table_images = True
        pipeline_options.accelerator_options = AcceleratorOptions(
            num_threads=self.num_threads, device=device
        )

        doc_converter = DocumentConverter(
            allowed_formats=[
                InputFormat.PDF,
                InputFormat.DOCX,
                InputFormat.PPTX,
            ],
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                    backend=DoclingParseV2DocumentBackend,
                )
            },
        )
        result = doc_converter.convert(source)

        return self.process_manager.process_document(result.document)
