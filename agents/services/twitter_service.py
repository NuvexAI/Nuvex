import logging
import time

import requests

from agents.common.config import SETTINGS
from agents.models.mongo_db import TwitterUser, find_by_username, save_twitter_user, TwitterPost

logger = logging.getLogger(__name__)


def get_twitter_user_by_username(username) -> TwitterUser:
    ret = find_by_username(username=username)
    if ret:
        now = int(time.time())
        update_at = ret.update_at
        if update_at > 0 and update_at > now - 60 * 30:
            logger.info(f"cached get_twitter_user_by_username_svc {username}")
            return ret

    ret = _get_user_by_username(username=username)

    if "data" not in ret:
        return None

    user = TwitterUser(
        username=ret["data"]["username"],
        name=ret["data"]["name"],
        user_id=ret["data"]["id"],
        description=ret["data"]["description"],
        verified_type=ret["data"]["verified_type"],
        profile_image_url=ret["data"]["profile_image_url"],
    )
    if "public_metrics" in ret["data"]:
        user.like_count = ret["data"]["public_metrics"]["like_count"] or 0
        user.media_count = ret["data"]["public_metrics"]["media_count"] or 0
        user.tweet_count = ret["data"]["public_metrics"]["tweet_count"] or 0
        user.listed_count = ret["data"]["public_metrics"]["listed_count"] or 0
        user.followers_count = ret["data"]["public_metrics"]["followers_count"] or 0
        user.following_count = ret["data"]["public_metrics"]["following_count"] or 0

    posts_ret = _get_posts_by_user_id(user.user_id)

    media_dict = {}
    if 'includes' in posts_ret:
        includes = posts_ret['includes']
        medias = includes.get('media', [])
        for media in medias:
            media_dict[media['media_key']] = media

    posts = []

    if 'data' in posts_ret:
        for tweet in posts_ret['data']:
            media_image_urls = []
            media_keys = tweet.get('attachments', {}).get('media_keys', [])

            for media_key in media_keys:
                media_info = media_dict.get(media_key, {})
                media_image_url = media_info.get('preview_image_url', '') or media_info.get('url', '')
                if media_image_url:
                    media_image_urls.append(media_image_url)

            x_id = tweet.get('id', '')

            metadata = TwitterPost(
                content=tweet.get('text'),
                created_at=tweet.get('created_at'),
                media_image_urls=media_image_urls,
                x_id=x_id,
                x_post_url=f"https://x.com/{username}/status/{x_id}"
            )

            posts.append(metadata)

    user.recent_posts = posts
    user.update_at = int(time.time())
    save_twitter_user(user)
    return user


def _get_user_by_username(username) -> dict:
    try:
        url = f"https://api.twitter.com/2/users/by/username/{username}"
        headers = {"Authorization": f"Bearer {SETTINGS.TWITTER_TOKEN}"}

        user_fields = [
            "description",
            "id",
            "name",
            "profile_image_url",
            "public_metrics",
            "username",
            "verified_type",
        ]
        params = {
            "expansions": "pinned_tweet_id",
            "user.fields": ",".join(user_fields),
        }

        response = requests.get(url, headers=headers, params=params)

        return response.json()
    except Exception as e:
        logger.error(e)
        return None


def _get_posts_by_user_id(user_id):
    try:
        url = f"https://api.x.com/2/users/{user_id}/tweets"
        headers = {
            'Authorization': f"Bearer {SETTINGS.TWITTER_TOKEN}",
        }

        params = {
            'max_results': 5,
            'tweet.fields': 'created_at,author_id',
            'expansions': 'attachments.media_keys,author_id',
            'media.fields': 'url,preview_image_url',
        }

        response = requests.get(url, headers=headers, params=params)
        return response.json()
    except Exception as e:
        return None
