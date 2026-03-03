# app/s3.py
import aioboto3
from botocore.config import Config
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class S3Service:
    def __init__(self):
        self.session = aioboto3.Session()
        self.config = Config(
            connect_timeout=30,
            read_timeout=300,  # 5 минут на скачивание
            retries={'max_attempts': 3}
        )

    async def _get_client(self):
        return self.session.client(
            's3',
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            config=self.config
        )

    async def list_files(self, bucket: str) -> list[dict]:
        """Список файлов в бакете"""
        try:
            async with await self._get_client() as client:
                response = await client.list_objects_v2(Bucket=bucket)
                
                files = []
                for obj in response.get('Contents', []):
                    key = obj['Key']
                    if not key.endswith('/'):
                        files.append({
                            'key': key,
                            'name': key.split('/')[-1],
                            'size': obj['Size']
                        })
                return files
        except Exception as e:
            logger.error(f"Error listing files in {bucket}: {e}")
            raise

    async def get_file(self, bucket: str, s3_key: str) -> bytes:
        """Скачать файл"""
        logger.info(f"Downloading {s3_key} from {bucket}")
        try:
            async with await self._get_client() as client:
                response = await client.get_object(Bucket=bucket, Key=s3_key)
                data = await response['Body'].read()
                logger.info(f"Downloaded {len(data)} bytes")
                return data
        except Exception as e:
            logger.error(f"Error downloading {s3_key}: {e}")
            raise

    async def get_presigned_url(self, bucket: str, s3_key: str, expires_in: int = 3600) -> str:
        """Временная ссылка на скачивание (1 час по умолчанию)"""
        logger.info(f"Generating presigned URL for {s3_key}")
        try:
            async with await self._get_client() as client:
                url = await client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': s3_key},
                    ExpiresIn=expires_in
                )
                return url
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise


s3 = S3Service()