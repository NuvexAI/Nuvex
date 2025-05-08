import logging
import uuid
from abc import ABC, abstractmethod
from typing import TypedDict, Union

import boto3
from botocore.exceptions import ClientError
from fastapi import Depends
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import RedirectResponse

from agents.common.config import SETTINGS
from agents.exceptions import CustomAgentException, ErrorCode
from agents.models.db import get_db
from agents.models.models import FileStorage

logger = logging.getLogger(__name__)

async def upload_file(
        file: UploadFile,
        session: AsyncSession = Depends(get_db)):
    """
    Upload file with user context
    """
    try:
        storage = Storage.get_storage(session)
        fid = await storage.upload_file(file, file.filename)
        return {"fid": fid, "url": f"/api/files/{fid}", "full_path": f"{SETTINGS.API_BASE_URL}/api/files/{fid}"}
    except Exception as e:
        logger.error(f"Error uploading file: {e}", exc_info=True)
        raise CustomAgentException(ErrorCode.API_CALL_ERROR, str(e))


async def query_file(file_uuid: str, session: AsyncSession = Depends(get_db)):
    try:
        storage = Storage.get_storage(session)
        
        # Check if it's S3 storage, if so, get presigned URL and redirect
        if isinstance(storage, S3Storage):
            # First check if the file exists
            file_exists = await storage.check_file_exists(file_uuid)
            if not file_exists:
                raise CustomAgentException(ErrorCode.RESOURCE_NOT_FOUND, "File not found")
                
            # Get presigned URL and redirect
            presigned_url = await storage.get_presigned_url(file_uuid)
            if presigned_url:
                logger.info(f"Generated S3 presigned URL and redirecting: {file_uuid}")
                return RedirectResponse(url=presigned_url)
        
        # If not S3 storage or unable to get presigned URL, fall back to regular method
        file_record: FileInfo = await storage.get_file(file_uuid)
        if not file_record:
            raise CustomAgentException(ErrorCode.RESOURCE_NOT_FOUND, "File not found")
        return file_record
    except CustomAgentException:
        raise
    except Exception as e:
        logger.error(f"Error querying file: {e}", exc_info=True)
        raise CustomAgentException(ErrorCode.API_CALL_ERROR, str(e))


class FileInfo(TypedDict):
    file_name: str
    file_data: bytes
    file_id: str
    file_size: int


class Storage(ABC):
    @abstractmethod
    def upload_file(self, file: UploadFile, file_name: str) -> str:
        pass

    @abstractmethod
    def delete_file(self, file_name: str) -> dict:
        pass

    @abstractmethod
    def get_file(self, file_name: str) -> Union[FileInfo, None]:
        pass

    @staticmethod
    def get_storage(session: AsyncSession):
        if SETTINGS.STORAGE_TYPE.lower() == "s3":
            storage = S3Storage(session)
        else:
            storage = DatabaseStorage(session)
        return storage


class DatabaseStorage(Storage):
    def __init__(self, session: AsyncSession):
        self.db_session = session

    async def upload_file(
            self,
            file: UploadFile,
            file_name: str,
            # tenant_id: str = None  # Add tenant_id parameter
        ) -> str:
        """
        Upload file to database with tenant context
        """
        file_uuid = str(uuid.uuid4())
        file_content = file.file.read()
        new_file = FileStorage(
            file_uuid=file_uuid,
            file_name=file_name,
            file_content=file_content,
            size=file.size,
            # tenant_id=tenant_id  # Add tenant_id
        )
        self.db_session.add(new_file)
        await self.db_session.commit()
        return file_uuid

    async def delete_file(self, file_location: str) -> dict:
        pass

    async def get_file(self, fid: str) -> Union[FileInfo, None]:
        result = await self.db_session.execute(select(FileStorage).where(FileStorage.file_uuid == fid))
        first = result.scalars().first()
        if first:
            return FileInfo(
                file_name=first.file_name,
                file_data=first.file_content,
                file_id=first.file_uuid,
                file_size=first.size,
            )
        return None


class S3Storage(Storage):
    def __init__(self, session: AsyncSession):
        self.db_session = session
        self.s3_client = self._get_s3_client()
        self.bucket = SETTINGS.AWS_S3_BUCKET
        self.prefix = SETTINGS.AWS_S3_PREFIX
        self.url_expiration = SETTINGS.AWS_S3_URL_EXPIRATION

    def _get_s3_client(self):
        """Create S3 client connection"""
        s3_config = {
            'aws_access_key_id': SETTINGS.AWS_ACCESS_KEY_ID,
            'aws_secret_access_key': SETTINGS.AWS_SECRET_ACCESS_KEY,
            'region_name': SETTINGS.AWS_REGION,
        }
        
        # If custom endpoint is set, use it (for S3-compatible storage services like MinIO)
        if SETTINGS.AWS_S3_ENDPOINT_URL:
            s3_config['endpoint_url'] = SETTINGS.AWS_S3_ENDPOINT_URL
            
        return boto3.client('s3', **s3_config)

    async def upload_file(self, file: UploadFile, file_name: str) -> str:
        """
        Upload file to S3 storage
        """
        file_uuid = str(uuid.uuid4())
        file_content = file.file.read()
        file_size = len(file_content)
        s3_key = f"{self.prefix}{file_uuid}/{file_name}"
        
        # Get content type, if file object doesn't provide it, guess from filename
        content_type = file.content_type
        if not content_type:
            content_type = self._guess_content_type(file_name)
        
        try:
            # Upload to S3 with correct content type
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type
            )
            
            logger.info(f"File uploaded to S3: {file_uuid}, size: {file_size}, type: {content_type}")
            
            # Save file metadata in database
            new_file = FileStorage(
                file_uuid=file_uuid,
                file_name=file_name,
                file_content=None,  # Don't store file content in database
                size=file_size,
                storage_location=s3_key,
                storage_type="s3"
            )
            self.db_session.add(new_file)
            await self.db_session.commit()
            
            return file_uuid
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}", exc_info=True)
            raise CustomAgentException(ErrorCode.API_CALL_ERROR, f"S3 upload failed: {str(e)}")

    async def delete_file(self, file_uuid: str) -> dict:
        """
        Delete file from S3
        """
        try:
            # Query file metadata
            result = await self.db_session.execute(select(FileStorage).where(FileStorage.file_uuid == file_uuid))
            file_record = result.scalars().first()
            
            if not file_record or file_record.storage_type != "s3":
                return {"success": False, "message": "File does not exist or is not S3 storage"}
                
            # Delete file from S3
            self.s3_client.delete_object(
                Bucket=self.bucket,
                Key=file_record.storage_location
            )
            
            # Delete record from database
            await self.db_session.delete(file_record)
            await self.db_session.commit()
            
            return {"success": True, "message": "File deleted"}
        except ClientError as e:
            logger.error(f"Error deleting file from S3: {e}", exc_info=True)
            raise CustomAgentException(ErrorCode.API_CALL_ERROR, f"S3 deletion failed: {str(e)}")

    async def get_file(self, file_uuid: str) -> Union[FileInfo, None]:
        """
        Get file from S3
        """
        try:
            # Query file metadata
            result = await self.db_session.execute(select(FileStorage).where(FileStorage.file_uuid == file_uuid))
            file_record = result.scalars().first()
            
            if not file_record or file_record.storage_type != "s3":
                return None
                
            # Get file content from S3
            response = self.s3_client.get_object(
                Bucket=self.bucket,
                Key=file_record.storage_location
            )
            
            file_data = response['Body'].read()
            
            return FileInfo(
                file_name=file_record.file_name,
                file_data=file_data,
                file_id=file_record.file_uuid,
                file_size=file_record.size,
            )
        except ClientError as e:
            logger.error(f"Error retrieving file from S3: {e}", exc_info=True)
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            raise CustomAgentException(ErrorCode.API_CALL_ERROR, f"S3 retrieval failed: {str(e)}")
            
    async def check_file_exists(self, file_uuid: str) -> bool:
        """
        Check if file exists in S3
        """
        try:
            # Query file metadata
            result = await self.db_session.execute(select(FileStorage).where(FileStorage.file_uuid == file_uuid))
            file_record = result.scalars().first()
            
            if not file_record or file_record.storage_type != "s3":
                return False
                
            # Check if object exists in S3
            try:
                self.s3_client.head_object(
                    Bucket=self.bucket,
                    Key=file_record.storage_location
                )
                return True
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    return False
                raise
        except Exception as e:
            logger.error(f"Error checking file existence in S3: {e}", exc_info=True)
            return False
            
    async def get_presigned_url(self, file_uuid: str) -> Union[str, None]:
        """
        Get presigned URL for S3 object
        """
        try:
            # Query file metadata
            result = await self.db_session.execute(select(FileStorage).where(FileStorage.file_uuid == file_uuid))
            file_record = result.scalars().first()
            
            if not file_record or file_record.storage_type != "s3":
                logger.warning(f"Cannot generate presigned URL: File does not exist or is not S3 storage - {file_uuid}")
                return None
                
            # Guess content type based on file extension
            content_type = self._guess_content_type(file_record.file_name)
                
            # Generate presigned URL
            try:
                presigned_url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.bucket,
                        'Key': file_record.storage_location,
                        'ResponseContentType': content_type,
                        'ResponseContentDisposition': f'attachment; filename="{file_record.file_name}"',
                    },
                    ExpiresIn=self.url_expiration
                )
                
                logger.info(f"Successfully generated presigned URL: {file_uuid}")
                return presigned_url
            except ClientError as e:
                logger.error(f"S3 client error when generating presigned URL: {e}", exc_info=True)
                return None
        except Exception as e:
            logger.error(f"Error generating presigned URL: {e}", exc_info=True)
            return None
            
    def _guess_content_type(self, filename: str) -> str:
        """
        Guess content type based on filename
        """
        import mimetypes
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or 'application/octet-stream'
