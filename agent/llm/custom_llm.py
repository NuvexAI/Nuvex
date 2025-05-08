from langchain_openai import ChatOpenAI

from agents.agent.llm.model import Model
from agents.common.config import SETTINGS
from agents.models.entity import ModelInfo


class CustomChat(Model):

    def __init__(self, model: ModelInfo):
        super().__init__()
        self.model = ChatOpenAI(
            openai_api_key=model.api_key,
            base_url=model.endpoint,
            model_name=model.model_name,
            temperature=SETTINGS.MODEL_TEMPERATURE,
        )

    def get_model(self):
        return self.model
