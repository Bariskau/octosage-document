from minio import Minio
from octosage.storage.base import BaseStorage
from io import BytesIO
from datetime import timedelta


class S3Storage(BaseStorage):

    def __init__(
        self,
        bucket_name: str,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        secure: bool = False,
    ):
        """
        Initialize Minio storage handler
        """
        self.bucket_name = bucket_name

        endpoint = endpoint_url.replace("http://", "").replace("https://", "")

        # Initialize Minio client
        self.client = Minio(
            endpoint, access_key=access_key, secret_key=secret_key, secure=secure
        )

        # Bucket yoksa oluştur
        if not self.client.bucket_exists(self.bucket_name):
            self.client.make_bucket(self.bucket_name)

    def save_file(self, content: bytes, filename: str) -> str:
        """
        Save file to Minio and return a presigned URL
        """
        try:
            # BytesIO kullanarak bytes'ı stream'e çevir
            file_data = BytesIO(content)
            file_size = len(content)

            # Upload the file
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=filename,
                data=file_data,
                length=file_size,
            )

            # Generate presigned URL (24 saat geçerli)
            presigned_url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=filename,
                expires=timedelta(days=1),  # 24 saat için timedelta kullanıyoruz
            )

            return presigned_url

        except Exception as e:
            raise Exception(f"Failed to upload file to Minio: {str(e)}")

    def get_file(self, file_path: str) -> bytes:
        """
        Get file from Minio
        """
        try:
            # Get object data
            data = self.client.get_object(
                bucket_name=self.bucket_name, object_name=file_path
            )
            # Read all data and return as bytes
            return data.read()

        except Exception as e:
            raise Exception(f"Failed to download file from Minio: {str(e)}")
