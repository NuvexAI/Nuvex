from fastapi import APIRouter

from agents.agent.prompts.tool_prompts import tool_prompt
from agents.common.response import RestResponse

router = APIRouter()


@router.get("/prompt/getDefaultToolPrompt")
async def get_default_tool_prompt():
    """
    Retrieve the default tool prompt.

    This endpoint returns a default tool prompt to guide the AI agent on how to use tools.
    
    Returns:
        RestResponse: Contains the data of the default tool prompt.
    """
    return RestResponse(data=tool_prompt())


@router.get("/prompt/getDefaultSystemPrompt")
async def get_system_prompt():
    """
    Retrieve the default system prompt.

    This endpoint returns a default system prompt, describing the basic functions and capabilities of the AI agent.
    
    Returns:
        RestResponse: Contains the data of the default system prompt.
    """
    system_prompt = "You are an AI Agent.You can solve problems directly or utilize specialized tools to perform detailed tasks and deliver precise solutions."""
    return RestResponse(data=system_prompt)
