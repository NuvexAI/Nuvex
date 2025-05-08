import asyncio
import logging

import aiohttp

from agents.common.config import SETTINGS

logger = logging.getLogger(__name__)


async def ai_search(query: str):
    """
    Generate coins research report for a given query.

    Args:
        query (str): A string representing the coin identifier, which can be either a coin symbol (e.g., "BTC") or a coin name. Alternatively, it can represent one or more contract addresses for tokens. If specifying multiple contract addresses, they should be provided as a comma-separated list.
    Returns:
        dict: A dictionary containing the generated report data.
    """
    url = SETTINGS.AI_SEARCH_HOST + "/api/deepcore/ai/search"
    headers = {
        "accept": "text/event-stream",
        "x-api-key": SETTINGS.AI_SEARCH_KEY
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params={"query": query}) as response:
            if response.status == 200:
                try:
                    async for line in response.content:
                        yield line.decode("utf-8")
                except asyncio.CancelledError:
                    logger.info("Request cancelled")
            else:
                yield f"Request failed with status code: {response.status}"
