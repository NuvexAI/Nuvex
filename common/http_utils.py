import base64

import aiohttp
from starlette.responses import JSONResponse


def add_cors_headers(response: JSONResponse):
    # response.headers["Access-Control-Allow-Origin"] = "*"
    # response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
    # response.headers["Access-Control-Allow-Headers"] = "*"
    return response


async def url_to_base64(image_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as response:
            response.raise_for_status()
            content = await response.read()
            encoded_data = base64.b64encode(content).decode("utf-8")
            return "data:image/png;base64," + encoded_data

image_base64_cache = {}

async def fetch_image_as_base64(image_url):
    if image_url in image_base64_cache:
        return image_base64_cache[image_url]

    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as response:
            response.raise_for_status()
            image_bytes = await response.read()
            encoded_base64 = base64.b64encode(image_bytes).decode("utf-8")
            base64_data = "data:image/png;base64," + encoded_base64
            image_base64_cache[image_url] = base64_data
            return base64_data
