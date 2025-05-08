from typing import List, Dict

from langchain_core.documents import Document
from langchain_core.tools import BaseTool


class ScoreCalculatorTool(BaseTool):
    name = "advanced_score_calculator"
    description = (
        "Calculates an advanced score for a given Document based on "
        "multiple metadata factors, including text sentiment, user verification, "
        "public engagement metrics, keyword occurrences, and more."
    )

    def _run(self, document: Document) -> float:
        score = 0

        text_length = len(document.page_content)
        score += min(text_length / 500, 1.0)

        # Scoring based on user verification status
        if document.metadata.get("verified"):
            score += 0.5

        # Scoring based on public engagement metrics
        public_metrics = document.metadata.get("public_metrics", {})
        likes = public_metrics.get("like_count", 0)
        retweets = public_metrics.get("retweet_count", 0)
        comments = public_metrics.get("reply_count", 0)
        engagement_score = (likes + retweets + comments) / 1000
        score += min(engagement_score, 1.0)  # Max 1.0 for engagement

        # Scoring based on presence of media
        if document.metadata.get("media_image_urls"):
            score += 0.5

        sentiment_score = self._analyze_sentiment(document.page_content)
        score += sentiment_score

        important_keywords = ['important', 'urgent', 'breaking']
        keyword_score = self._keyword_frequency_score(document.page_content, important_keywords)
        score += keyword_score

        historical_behavior_score = self._user_behavior_influence(document.metadata)
        score += historical_behavior_score

        # Normalize score to a maximum of 5.0
        final_score = min(score, 5.0)
        return final_score

    def _analyze_sentiment(self, text: str) -> float:
        positive_keywords = ['good', 'great', 'excellent']
        negative_keywords = ['bad', 'poor', 'terrible']
        positive_count = sum(text.lower().count(word) for word in positive_keywords)
        negative_count = sum(text.lower().count(word) for word in negative_keywords)

        if positive_count > negative_count:
            return 0.5
        elif negative_count > positive_count:
            return -0.5
        return 0.0

    def _keyword_frequency_score(self, text: str, keywords: List[str]) -> float:
        total_occurrences = sum(text.lower().count(keyword) for keyword in keywords)
        return min(total_occurrences / 10, 1.0)

    def _user_behavior_influence(self, metadata: Dict) -> float:
        if metadata.get("username") == "high_influencer":
            return 0.5
        return 0.0
