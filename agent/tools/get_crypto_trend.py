import asyncio
import datetime
import random
from typing import List, Dict, Any

from langchain_core.tools import BaseTool
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel


class CryptoTrendQuery(BaseModel):
    symbol: str
    interval: int = 1
    duration: int = 10


class GetCryptoTrendTool(BaseTool):

    def __init__(self, mongo_uri: str, db_name="deepcore", collection_name="crypto_trend"):
        self.client = AsyncIOMotorClient(mongo_uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    async def _arun(self, query: CryptoTrendQuery) -> List[Dict[str, Any]]:
        symbol = query.symbol
        interval = query.interval
        duration = query.duration

        start_time = datetime.datetime.utcnow()
        end_time = start_time + datetime.timedelta(seconds=duration)

        trends = []

        while datetime.datetime.utcnow() < end_time:
            result = await self._get_latest_trend(symbol)
            if result:
                trends.append(result)
            await asyncio.sleep(interval)

        return trends

    async def _get_latest_trend(self, symbol: str) -> Dict[str, Any]:
        query = {"symbol": symbol}
        document = await self.collection.find_one(query, sort=[("timestamp", -1)])
        if document:
            latest_price = document.get('price_usd', 0) + random.uniform(-1, 1)  # Simulated price change
            trend = {
                "symbol": symbol,
                "price_usd": f"${latest_price:,.2f}",
                "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "change": random.choice(["up", "down"])  # Simulated trend direction
            }
            return trend
        return {}
