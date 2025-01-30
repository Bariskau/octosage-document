from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from pydantic import BaseModel
from typing import List
from pathlib import Path
import tempfile
import shutil
import json
from octosage.converters.doc_converter import DocConverter
from octosage.operations.sort_operation import SortOperation
from octosage.operations.transform_operation import TransformOperation
from octosage.settings import settings
import torch, gc

order_model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup: Create output directory
    Path(settings.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    yield
    # Cleanup code (if any) would go here


app = FastAPI(lifespan=lifespan)


class DocumentProcessingRequest(BaseModel):
    languages: List[str] = ["tr", "en"]
    force_full_page_ocr: bool = True
    images_scale: float = 2.0
    num_threads: int = 4


@app.post("/process")
async def process_and_sort(
    file: UploadFile = File(...),
    languages: str = Form(default='["tr", "en"]'),
    force_full_page_ocr: bool = Form(default=True),
    images_scale: float = Form(default=2.0),
    num_threads: int = Form(default=4),
):
    """
    Process and sort a document
    """
    try:
        # Parse languages from string to list
        languages_list = json.loads(languages)

        # Create params object
        params = DocumentProcessingRequest(
            languages=languages_list,
            force_full_page_ocr=force_full_page_ocr,
            images_scale=images_scale,
            num_threads=num_threads,
        )

        # Create a temporary directory to store the uploaded file
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = Path(temp_dir) / file.filename

            # Save uploaded file
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Initialize converter with parameters
            converter = DocConverter(
                languages=params.languages,
                force_full_page_ocr=params.force_full_page_ocr,
                images_scale=params.images_scale,
                num_threads=params.num_threads,
            )

            # Process document
            result = converter.convert(str(temp_file_path))

            torch.cuda.empty_cache()
            gc.collect()
            # Sort results
            sort_operator = SortOperation()
            sorted_result = sort_operator.sort(result)

            return {"status": "success", "result": sorted_result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/transform")
async def process_and_transform(
    file: UploadFile = File(...),
    languages: str = Form(default='["tr", "en"]'),
    force_full_page_ocr: bool = Form(default=True),
    images_scale: float = Form(default=2.0),
    num_threads: int = Form(default=4),
):
    """
    Process and transform a document
    """
    try:
        # Parse languages from string to list
        languages_list = json.loads(languages)

        # Create params object
        params = DocumentProcessingRequest(
            languages=languages_list,
            force_full_page_ocr=force_full_page_ocr,
            images_scale=images_scale,
            num_threads=num_threads,
        )

        # Create a temporary directory to store the uploaded file
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_file_path = Path(temp_dir) / file.filename

            # Save uploaded file
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # Initialize converter with parameters
            converter = DocConverter(
                languages=params.languages,
                force_full_page_ocr=params.force_full_page_ocr,
                images_scale=params.images_scale,
                num_threads=params.num_threads,
            )

            # Process document
            result = converter.convert(str(temp_file_path))

            # Sort first (as in the original code)
            sort_operator = SortOperation()
            sorted_result = sort_operator.sort(result)

            # Then transform
            transform_operator = TransformOperation(sorted_result)
            transformed_result = transform_operator.transform()

            return {"status": "success", "result": transformed_result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
