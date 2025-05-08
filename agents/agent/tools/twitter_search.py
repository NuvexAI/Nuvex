import logging
from typing import Any, List

import aiohttp
from langchain_core.documents import Document
from langchain_core.tools import BaseTool

from agents.common.config import SETTINGS

logger = logging.getLogger(__name__)

headers = {'Authorization': f'Bearer {SETTINGS.TWITTER_TOKEN}'}


class TwitterSearchTool(BaseTool):
    name = "XSearchOp"
    description = "Search operation for X platform"

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        pass

    async def _arun(self, *args: Any, **kwargs: Any) -> Any:

        query_params = {
            'query': args.query,
            'max_results': args.max_results,
            'tweet.fields': 'created_at,public_metrics,author_id',
            'media.fields': 'url,preview_image_url',
            'user.fields': 'name,profile_image_url,verified,verified_type',
            'expansions': 'attachments.media_keys,author_id',
        }

        async with aiohttp.ClientSession() as session:
            tweets = await self._fetch_tweets(session, headers, query_params)
            if not tweets:
                return []
            return await self._process_tweets(tweets, args.query)

    async def _fetch_tweets(self, session: aiohttp.ClientSession, headers: dict, params: dict) -> dict:
        search_url = "https://api.twitter.com/2/tweets/search/recent"
        async with session.get(search_url, headers=headers, params=params) as response:
            if response.status == 429:
                logger.warning(f"Rate limit exceeded")
                return {}
            response.raise_for_status()
            return await response.json()

    async def _process_tweets(self, tweets: dict, input_query: str) -> List[Document]:
        ret = []
        users_dict = {user["id"]: user for user in tweets.get('includes', {}).get('users', [])}
        media_dict = {media["media_key"]: media for media in tweets.get('includes', {}).get('media', [])}

        for tweet in tweets.get('data', []):
            author_info = users_dict.get(tweet.get("author_id", ""), {})
            media_image_urls = [
                media_dict[media_key].get('preview_image_url') or media_dict[media_key].get('url')
                for media_key in tweet.get('attachments', {}).get('media_keys', [])
                if media_key in media_dict
            ]

            doc = Document(
                page_content=tweet["text"],
                metadata={
                    "content": tweet["text"],
                    "created_at": tweet.get("created_at", ""),
                    "query": input_query,
                    "site": "x",
                    "verified": author_info.get("verified", False),
                    "username": author_info.get("username", ""),
                    "profile_image_url": author_info.get("profile_image_url", ""),
                    "verified_type": author_info.get("verified_type", ""),
                    "public_metrics": tweet.get("public_metrics", {}),
                    "media_image_urls": media_image_urls,
                }
            )
            ret.append(doc)

        return ret
