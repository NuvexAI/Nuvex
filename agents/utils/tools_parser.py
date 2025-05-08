import logging
from typing import List

from agents.models.entity import ToolInfo, ToolType
from agents.utils.parser import extract_md_code

looger = logging.getLogger(__name__)

def convert_tool_into_openai_schema(api_tool: List[ToolInfo]):
    """Convert a list of ToolInfo objects into an OpenAI API schema."""
    api_tool_schemas = []
    function_tool_schemas = []
    mcp_tool_schemas = []
    for tool in api_tool:
        tool_schema = {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        }
        if tool.type == ToolType.FUNCTION.value:
            function_tool_schemas.append(tool_schema)
        elif tool.type == ToolType.OPENAPI.value:
            api_tool_schemas.append(tool_schema)
        elif tool.type == ToolType.MCP.value:
            mcp_tool_schemas.append(tool_schema)

    api_schemas = {}
    function_schemas = {}
    if api_tool_schemas:
        api_schemas = {
            "type": "api",
            "functions": [
                schema for schema in api_tool_schemas
            ],
        }

    if function_tool_schemas:
        function_schemas = {
            "type": "function",
            "functions": [
                schema for schema in function_tool_schemas
            ],
        }

    mcp_schemas = {}
    if mcp_tool_schemas:
        mcp_schemas = {
            "type": "mcp",
            "functions": [
                schema for schema in mcp_tool_schemas
            ],
        }
    return api_schemas,  function_schemas, mcp_schemas


def parse_and_execute_json(json: str):
    """Parse and execute a JSON string."""
    try:
        json_string = extract_md_code(json)
        data = json.loads(json_string)
        return data
    except json.JSONDecodeError as e:
        looger.error(f"Invalid JSON: {e}")
    return None