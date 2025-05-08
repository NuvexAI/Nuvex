import concurrent
import inspect
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from agents.utils.parser import func_to_str, functions_to_str, get_openai_function_schema_from_func, \
    load_basemodels_if_needed, single_pydantic_to_openai_function, pydantic_to_function_call

logger = logging.getLogger(__name__)

ToolType = Union[BaseModel, Dict[str, Any], Callable[..., Any]]


def func_to_dict(
        function: Callable[..., Any] = None,
        name: Optional[str] = None,
        description: str = None,
        *args,
        **kwargs,
) -> Dict[str, Any]:
    try:
        return get_openai_function_schema_from_func(
            function=function,
            name=name,
            description=description,
            *args,
            **kwargs,
        )
    except Exception as e:
        logger.error(f"An error occurred in func_to_dict: {e}")
        logger.error(
            "Please check the function and ensure it is valid."
        )
        logger.error(
            "If the issue persists, please seek further assistance."
        )
        raise


def load_params_from_func_for_pybasemodel(
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
) -> Callable[..., Any]:
    try:
        return load_basemodels_if_needed(func, *args, **kwargs)
    except Exception as e:
        logger.error(
            f"An error occurred in load_params_from_func_for_pybasemodel: {e}"
        )
        logger.error(
            "Please check the function and ensure it is valid."
        )
        logger.error(
            "If the issue persists, please seek further assistance."
        )
        raise


def base_model_to_dict(
        pydantic_type: type[BaseModel],
        output_str: bool = False,
        *args: Any,
        **kwargs: Any,
) -> dict[str, Any]:
    try:
        return single_pydantic_to_openai_function(
            pydantic_type, output_str, *args, **kwargs
        )
    except Exception as e:
        logger.error(
            f"An error occurred in base_model_to_dict: {e}"
        )
        logger.error(
            "Please check the Pydantic type and ensure it is valid."
        )
        logger.error(
            "If the issue persists, please seek further assistance."
        )
        raise


def dict_to_openai_schema_str(
        dict: dict[str, Any],
) -> str:
    try:
        return func_to_str(dict)
    except Exception as e:
        logger.error(
            f"An error occurred in dict_to_openai_schema_str: {e}"
        )
        logger.error(
            "Please check the dictionary and ensure it is valid."
        )
        logger.error(
            "If the issue persists, please seek further assistance."
        )
        raise


def multi_dict_to_openai_schema_str(
        dicts: list[dict[str, Any]],
) -> str:
    try:
        return functions_to_str(dicts)
    except Exception as e:
        logger.error(
            f"An error occurred in multi_dict_to_openai_schema_str: {e}"
        )
        logger.error(
            "Please check the dictionaries and ensure they are valid."
        )
        logger.error(
            "If the issue persists, please seek further assistance."
        )
        raise


def get_docs_from_callable(item):
    try:
        return process_tool_docs(item)
    except Exception as e:
        logger.error(f"An error occurred in get_docs: {e}")
        logger.error(
            "Please check the item and ensure it is valid."
        )
        logger.error(
            "If the issue persists, please seek further assistance."
        )
        raise


def detect_tool_input_type(input: ToolType) -> str:
    if isinstance(input, BaseModel):
        return "Pydantic"
    elif isinstance(input, dict):
        return "Dictionary"
    elif callable(input):
        return "Function"
    else:
        return "Unknown"


def check_func_if_have_docs(func: callable):
    if func.__doc__ is not None:
        return True
    else:
        logger.error(
            f"Function {func.__name__} does not have documentation"
        )
        raise ValueError(
            f"Function {func.__name__} does not have documentation"
        )


def check_func_if_have_type_hints(func: callable):
    if func.__annotations__ is not None:
        return True
    else:
        logger.info(
            f"Function {func.__name__} does not have type hints"
        )
        raise ValueError(
            f"Function {func.__name__} does not have type hints"
        )


class BaseTool(BaseModel):
    pydantic_base_models: Optional[List[type[BaseModel]]] = None
    tools: Optional[List[Callable[..., Any]]] = None
    tool_system_prompt: Optional[str] = Field(None, description="The system prompt for the tool system.", )
    func_tool: Optional[bool] = None
    func_map: Optional[Dict[str, Callable]] = None
    list_of_dicts: Optional[List[Dict[str, Any]]] = None

    def multi_base_models_to_dict(
            self, return_str: bool = False, *args, **kwargs
    ) -> dict[str, Any]:
        try:
            if return_str:
                return pydantic_to_function_call(
                    self.pydantic_base_models, *args, **kwargs
                )
            else:
                return pydantic_to_function_call(
                    self.pydantic_base_models, *args, **kwargs
                )
        except Exception as e:
            logger.error(
                f"An error occurred in multi_base_models_to_dict: {e}"
            )
            logger.error(
                "Please check the Pydantic types and ensure they are valid."
            )
            logger.error(
                "If the issue persists, please seek further assistance."
            )
            raise

    def execute_tool(
            self,
            *args: Any,
            **kwargs: Any,
    ) -> Callable:
        try:
            return openai_tool_executor(
                self.list_of_dicts,
                self.func_map,
                *args,
                **kwargs,
            )
        except Exception as e:
            logger.error(f"An error occurred in execute_tool: {e}")
            logger.error(
                "Please check the tools and function map and ensure they are valid."
            )
            logger.error(
                "If the issue persists, please seek further assistance."
            )
            raise

    def dynamic_run(self, input: Any) -> str:
        tool_input_type = detect_tool_input_type(input)
        if tool_input_type == "Pydantic":
            function_str = single_pydantic_to_openai_function(input)
        elif tool_input_type == "Dictionary":
            function_str = func_to_str(input)
        elif tool_input_type == "Function":
            function_str = get_openai_function_schema_from_func(input)
        else:
            return "Unknown tool input type"

        if self.func_tool:
            if tool_input_type == "Function":
                # Add the function to the functions list
                self.tools.append(input)

            # Create a function map from the functions list
            function_map = {
                func.__name__: func for func in self.tools
            }

            # Execute the tool
            return self.execute_tool(
                tools=[function_str], function_map=function_map
            )
        else:
            return function_str

    def execute_tool_by_name(
            self,
            tool_name: str,
    ) -> Any:
        # Search for the tool by name
        tool = next(
            (
                tool
                for tool in self.tools
                if tool.get("name") == tool_name
            ),
            None,
        )

        # If the tool is not found, raise an error
        if tool is None:
            raise ValueError(f"Tool '{tool_name}' not found")

        # Get the function associated with the tool
        func = self.func_map.get(tool_name)

        # If the function is not found, raise an error
        if func is None:
            raise TypeError(
                f"Tool '{tool_name}' is not mapped to a function"
            )

        # Execute the tool
        return func(**tool.get("parameters", {}))

    def execute_tool_from_text(self, text: str) -> Any:
        # Convert the text into a dictionary
        tool = json.loads(text)

        # Get the tool name and parameters from the dictionary
        tool_name = tool.get("name")
        tool_params = tool.get("parameters", {})

        # Get the function associated with the tool
        func = self.func_map.get(tool_name)

        # If the function is not found, raise an error
        if func is None:
            raise TypeError(
                f"Tool '{tool_name}' is not mapped to a function"
            )

        # Execute the tool
        return func(**tool_params)

    def check_str_for_functions_valid(self, output: str):
        try:
            # Parse the output as JSON
            data = json.loads(output)

            # Check if the output matches the schema
            if (
                    data.get("type") == "function"
                    and "function" in data
                    and "name" in data["function"]
            ):

                # Check if the function name matches any name in the function map
                function_name = data["function"]["name"]
                if function_name in self.func_map:
                    return True

        except json.JSONDecodeError:
            logger.error("Error decoding JSON with output")
            pass

        return False

    def convert_funcs_into_tools(self):
        if self.tools is not None:
            logger.info(
                "Tools provided make sure the functions have documentation ++ type hints, otherwise tool execution won't be reliable."
            )

            # Log the tools
            logger.info(
                f"Tools provided: Accessing {len(self.tools)} tools"
            )

            # Transform the tools into an openai schema
            self.convert_tool_into_openai_schema()

            # Now update the function calling map for every tools
            self.func_map = {
                tool.__name__: tool for tool in self.tools
            }

        return None

    def convert_tool_into_openai_schema(self):
        logger.info(
            "Converting tools into OpenAI function calling schema"
        )

        tool_schemas = []

        for tool in self.tools:
            # Transform the tool into a openai function calling schema
            if check_func_if_have_docs(
                    tool
            ) and check_func_if_have_type_hints(tool):
                name = tool.__name__
                description = tool.__doc__

                logger.info(
                    f"Converting tool: {name} into a OpenAI certified function calling schema. Add documentation and type hints."
                )
                tool_schema = get_openai_function_schema_from_func(
                    tool, name=name, description=description
                )

                logger.info(
                    f"Tool {name} converted successfully into OpenAI schema"
                )

                tool_schemas.append(tool_schema)
            else:
                logger.error(
                    f"Tool {tool.__name__} does not have documentation or type hints, please add them to make the tool execution reliable."
                )

        # Combine all tool schemas into a single schema
        if tool_schemas:
            combined_schema = {
                "type": "function",
                "functions": [
                    schema["function"] for schema in tool_schemas
                ],
            }
            return json.dumps(combined_schema, indent=4)

        return None


def openai_tool_executor(
        tools: List[Dict[str, Any]],
        function_map: Dict[str, Callable],
        return_as_string: bool = False,
        *args,
        **kwargs,
) -> Callable:
    def tool_executor():
        results = []
        logger.info(f"Executing {len(tools)} tools concurrently.")
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = []
            for tool in tools:
                if tool.get("type") != "function":
                    continue

                function_info = tool.get("function", {})
                func_name = function_info.get("name")
                logger.info(f"Executing function: {func_name}")

                if func_name not in function_map:
                    error_message = f"Function '{func_name}' not found in function map."
                    logger.error(error_message)
                    results.append(error_message)
                    continue

                params = function_info.get("parameters", {})
                if not params:
                    error_message = f"No parameters specified for function '{func_name}'."
                    logger.error(error_message)
                    results.append(error_message)
                    continue

                if "name" in params and params["name"] in function_map:
                    try:
                        result = function_map[params["name"]](
                            **params
                        )
                        results.append(f"{params['name']}: {result}")
                    except Exception as e:
                        error_message = f"Failed to execute the function '{params['name']}': {e}"
                        logger.error(error_message)
                        results.append(error_message)
                    continue

                try:
                    future = executor.submit(
                        function_map[func_name], **params
                    )
                    futures.append((func_name, future))
                except Exception as e:
                    error_message = f"Failed to submit the function '{func_name}' for execution: {e}"
                    logger.error(error_message)
                    results.append(error_message)

            for func_name, future in futures:
                try:
                    result = future.result()
                    results.append(f"{func_name}: {result}")
                except Exception as e:
                    error_message = f"Error during execution of function '{func_name}': {e}"
                    logger.error(error_message)
                    results.append(error_message)

        if return_as_string:
            return "\n".join(results)

        logger.info(f"Results: {results}")

        return results

    return tool_executor


def process_tool_docs(item):
    # If item is an instance of a class, get its class
    if not inspect.isclass(item) and hasattr(item, "__class__"):
        item = item.__class__

    doc = inspect.getdoc(item)
    source = inspect.getsource(item)
    is_class = inspect.isclass(item)
    item_type = "Class Name" if is_class else "Function Name"
    metadata = f"{item_type}: {item.__name__}\n\n"
    if doc:
        metadata += f"Documentation:\n{doc}\n\n"
    metadata += f"\n{source}"
    return metadata
