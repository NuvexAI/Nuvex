import logging
import os
import uuid

import aiohttp
import boto3

from agents.common.config import SETTINGS


async def download_and_upload_image(url, bucket_name):
    file_name = f"{uuid.uuid4()}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                content = await response.read()

                with open(file_name, 'wb') as f:
                    f.write(content)

                s3_client = boto3.client(
                    "s3",
                    region_name=SETTINGS.AWS_REGION,
                    aws_access_key_id=SETTINGS.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=SETTINGS.AWS_SECRET_ACCESS_KEY,
                )
                s3_client.put_object(
                    Bucket=bucket_name,
                    Key=file_name,
                    Body=content,
                    ACL="public-read",
                    ContentType=response.headers.get("Content-Type", "application/octet-stream")
                )
                fileurl = f"https://{bucket_name}.s3.{SETTINGS.AWS_REGION}.amazonaws.com/{file_name}"
                return fileurl

    except Exception as e:
        logging.error(f"download_and_upload_image {e}", exc_info=True)
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)
    return ""
