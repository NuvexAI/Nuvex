import json
import logging
from typing import List, Any, Callable, AsyncIterator

from agents.utils.parser import extract_md_code

logger = logging.getLogger(__name__)


async def async_execute(
        functions: List[Callable[..., Any]],
        json_string: str,
        parse_md: bool = False,
        *args: Any,
        **kwargs: Any
) -> AsyncIterator:
    """
    Execute a list of functions with the given JSON string as input.
    Args:
        functions (List[Callable[..., Any]]): A list of callables to execute.
        json_string (str): The JSON string containing the arguments for each function.
    Returns:
        dict: A dictionary containing the results from each function execution.
    """
    if not functions or not json_string:
        return

    if parse_md:
        json_string = extract_md_code(json_string)

    try:
        # Create function name to function mapping
        function_dict = {func.__name__: func for func in functions}

        # Parse JSON data
        data = json.loads(json_string)

        # Handle both single function and function list formats
        function_list = []
        if "functions" in data:
            function_list = data["functions"]
        elif "function" in data:
            function_list = [data["function"]]
        else:
            function_list = [
                data
            ]  # Assume entire object is single function

        # Ensure function_list is a list and filter None values
        if isinstance(function_list, dict):
            function_list = [function_list]
        function_list = [f for f in function_list if f]

        for function_data in function_list:
            function_name = function_data.get("name")
            parameters = function_data.get("parameters", {})

            if not function_name:
                logger.warning("Function data missing name field")
                continue

            if function_name not in function_dict:
                continue

            try:
                async for data in function_dict[function_name](**parameters):
                    yield data
            except Exception as e:
                logger.error(
                    f"Error executing {function_name}: {str(e)}"
                )
                yield f"{function_name} Error: {str(e)}"

    except json.JSONDecodeError as e:
        error = f"Invalid JSON format: {str(e)}"
        logger.error(error)
        # yield {"error": error}
    except Exception as e:
        error = f"Error parsing and executing JSON: {str(e)}"
        logger.error(error)
        # yield {"error": error}
