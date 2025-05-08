from typing import List, Dict, Any, Optional

from langchain_core.tools import BaseTool
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel


class CryptoQuery(BaseModel):
    symbol: Optional[str] = None
    name: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_market_cap: Optional[float] = None
    max_market_cap: Optional[float] = None
    sort_by: Optional[str] = None
    sort_order: Optional[str] = "asc"  # "asc" or "desc"
    limit: Optional[int] = 10
    offset: Optional[int] = 0


class GetCryptoDataTool(BaseTool):

    def __init__(self, mongo_uri: str, db_name: str = "deepcore", collection_name: str = "crypto_data"):
        self.client = AsyncIOMotorClient(mongo_uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

    async def _arun(self, query: CryptoQuery) -> List[Dict[str, Any]]:
        mongo_query = {}
        if query.symbol:
            mongo_query['symbol'] = query.symbol
        if query.name:
            mongo_query['name'] = {'$regex': query.name, '$options': 'i'}
        if query.min_price is not None:
            mongo_query['price_usd'] = mongo_query.get('price_usd', {})
            mongo_query['price_usd']['$gte'] = query.min_price
        if query.max_price is not None:
            mongo_query['price_usd'] = mongo_query.get('price_usd', {})
            mongo_query['price_usd']['$lte'] = query.max_price
        if query.min_market_cap is not None:
            mongo_query['market_cap_usd'] = mongo_query.get('market_cap_usd', {})
            mongo_query['market_cap_usd']['$gte'] = query.min_market_cap
        if query.max_market_cap is not None:
            mongo_query['market_cap_usd'] = mongo_query.get('market_cap_usd', {})
            mongo_query['market_cap_usd']['$lte'] = query.max_market_cap

        sort_order = 1 if query.sort_order == "asc" else -1
        sort_criteria = [(query.sort_by, sort_order)] if query.sort_by else None

        cursor = self.collection.find(mongo_query).skip(query.offset).limit(query.limit)
        if sort_criteria:
            cursor = cursor.sort(sort_criteria)

        results = await cursor.to_list(length=query.limit)
        return self._format_results(results)

    def _format_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        formatted_results = []
        for result in results:
            formatted_result = {
                "symbol": result.get("symbol"),
                "name": result.get("name"),
                "price_usd": f"${result.get('price_usd', 0):,.2f}",
                "market_cap_usd": f"${result.get('market_cap_usd', 0):,.2f}",
                "volume_24h": f"${result.get('volume_24h', 0):,.2f}",
                "timestamp": result.get("timestamp").strftime("%Y-%m-%d %H:%M:%S")
            }
            formatted_results.append(formatted_result)
        return formatted_results
