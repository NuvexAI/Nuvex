import copy
import json
import logging
from typing import Dict, Any, Tuple, List
from urllib.parse import urlparse

from prance import ResolvingParser

# Constants for parameter type suffixes
HEADER_SUFFIX = '_by_header'
PARAMS_SUFFIX = '_by_params'
PATH_SUFFIX = '_by_paths'

# Fields to be filtered out from the OpenAPI spec
filtered_fields = ['testcase']

logger = logging.getLogger(__name__)


def load_openapi_spec(spec_json: str) -> Dict[str, Any]:
    """
    Load and parse the OpenAPI specification.
    Filters out unnecessary fields.
    If filtering fails, falls back to the original spec_json.
    """
    try:
        parsed_json = json.loads(spec_json)
        filtered_spec = filter_specification_fields(parsed_json)
        filtered_json = json.dumps(filtered_spec, ensure_ascii=False)
    except Exception as e:
        logger.warning(f'Field filtering failed: {e}', exc_info=True)
        filtered_json = spec_json

    try:
        parser = ResolvingParser(spec_string=filtered_json, skip_validation=True)
    except Exception as e:
        logger.error(f'Parsing OpenAPI spec failed: {e}', exc_info=True)
        raise e

    return parser.specification


def filter_specification_fields(specification: Any) -> Any:
    """
    Recursively remove unnecessary fields from the OpenAPI specification.
    Supports both dict and list types.
    """
    if isinstance(specification, dict):
        new_spec = {}
        for key, value in specification.items():
            if key in filtered_fields:
                continue
            new_spec[key] = filter_specification_fields(value)
        return new_spec
    elif isinstance(specification, list):
        return [filter_specification_fields(item) for item in specification]
    else:
        return specification


def generate_schema_model(schema: Dict[str, Any]) -> Dict:
    """
    Recursively parse the schema to generate a simplified model.
    For object types, only the inner properties (and required list) are extracted.
    Supports object, array, and additionalProperties.
    """
    property_fields = {}
    for prop_name, prop_spec in schema.get('properties', {}).items():
        field_definition: Dict[str, Any] = {
            'type': prop_spec.get('type', 'object'),
            'description': prop_spec.get('description', '')
        }
        if 'default' in prop_spec:
            field_definition['default'] = prop_spec['default']
        if prop_spec.get('required'):
            field_definition['required'] = prop_spec['required']
        if prop_spec.get("enum"):
            field_definition['enum'] = prop_spec['enum']
        if field_definition['type'] == 'array' and 'items' in prop_spec:
            field_definition['items'] = generate_schema_model(prop_spec['items'])
        elif field_definition['type'] == 'object' and 'properties' in prop_spec:
            nested = generate_schema_model(prop_spec)
            field_definition['properties'] = nested.get('properties', {})
            if 'required' in nested:
                field_definition['required'] = nested['required']
        property_fields[prop_name] = field_definition

    schema_model = {
        'type': schema.get('type', 'object'),
        'properties': property_fields
    }
    if schema.get('description'):
        schema_model['description'] = schema['description']
    if schema.get('required'):
        schema_model['required'] = schema['required']
    if 'additionalProperties' in schema:
        schema_model['additionalProperties'] = schema['additionalProperties']

    return schema_model


def parse_parameters(parameters: List[Dict[str, Any]]) -> Tuple[Dict, Dict, Dict]:
    """
    Parse parameters from the OpenAPI spec and extract header, query, and path parameters.
    """
    header_params, query_params, path_params = {}, {}, {}
    for param in parameters:
        param_name = param.get('name')
        if not param_name:
            continue
        schema = param.get('schema', {})
        param_definition = {
            'type': schema.get('type', 'string'),
            'description': param.get('description', '')
        }
        if 'default' in schema:
            param_definition['default'] = schema.get('default')
        # elif 'example' in schema:
        #     param_definition['default'] = schema.get('example')
        if param.get('required'):
            param_definition['required'] = True

        param_location = param.get('in', '')
        if param_location == 'header':
            header_params[param_name] = param_definition
        elif param_location == 'path':
            path_params[param_name] = param_definition
        elif param_location == 'cookie':
            query_params[param_name] = param_definition
        else:
            query_params[param_name] = param_definition

    return header_params, query_params, path_params



def process_openapi_paths(openapi_spec: Dict[str, Any]) -> Tuple[Dict, Dict, Dict, Dict]:
    """
    Process paths in the OpenAPI spec and extract header, query, path parameters,
    as well as the requestBody schema (if any).
    For multiple operations under the same path, parameters are merged.
    """
    openapi_paths = openapi_spec.get('paths', {})
    header_params, query_params, path_params, request_schema = {}, {}, {}, {}
    for path, path_info in openapi_paths.items():
        for method, method_info in path_info.items():
            if not isinstance(method_info, dict):
                continue
            parameters = method_info.get('parameters', [])
            h_params, q_params, p_params = parse_parameters(parameters)
            header_params.update(h_params)
            query_params.update(q_params)
            path_params.update(p_params)
            request_body = method_info.get('requestBody', {})
            if request_body:
                request_body_content = request_body.get('content', {})
                for content_type, media_type_object in request_body_content.items():
                    schema = media_type_object.get('schema', {})
                    if schema and not request_schema:
                        request_schema = generate_schema_model(schema)
                        break
    return header_params, query_params, path_params, request_schema


def merge_parameters(header_params: Dict, query_params: Dict,
                     path_params: Dict, request_schema: Dict) -> Dict:
    """
    Merge all parameters into a single request schema.
    Suffixes are added to distinguish between parameter types.
    """
    merged_schema = copy.deepcopy(request_schema) if request_schema else {'type': 'object', 'properties': {}}
    merged_schema["properties"] = merged_schema.get('properties', {})
    required_fields = merged_schema.get('required', [])
    if not isinstance(required_fields, list):
        required_fields = [required_fields]

    for key, value in header_params.items():
        param_key = key + HEADER_SUFFIX
        merged_schema["properties"][param_key] = value
        if value.get('required'):
            required_fields.append(param_key)
            value.pop('required', None)

    for key, value in query_params.items():
        param_key = key + PARAMS_SUFFIX
        merged_schema["properties"][param_key] = value
        if value.get('required'):
            required_fields.append(param_key)
            value.pop('required', None)

    for key, value in path_params.items():
        param_key = key + PATH_SUFFIX
        merged_schema["properties"][param_key] = value
        if value.get('required'):
            required_fields.append(param_key)
            value.pop('required', None)

    if required_fields:
        merged_schema['required'] = list(set(required_fields))
    return merged_schema


def get_request_parameters(spec_json: str) -> Dict:
    """
    Extract and merge all parameters from the OpenAPI spec,
    returning the merged request schema.
    """
    openapi_spec = load_openapi_spec(spec_json)
    header_params, query_params, path_params, request_schema = process_openapi_paths(openapi_spec)
    return merge_parameters(header_params, query_params, path_params, request_schema)


def parse_request_args(args: Dict) -> Tuple[Dict, Dict, Dict, Dict]:
    """
    Parse request arguments and separate them into header, query, path, and body parameters.
    """
    header_params, query_params, path_params, body_params = {}, {}, {}, {}
    if isinstance(args, dict):
        for key, value in args.items():
            if key.endswith(HEADER_SUFFIX):
                header_params[key[:-len(HEADER_SUFFIX)]] = value
            elif key.endswith(PARAMS_SUFFIX):
                query_params[key[:-len(PARAMS_SUFFIX)]] = value
            elif key.endswith(PATH_SUFFIX):
                path_params[key[:-len(PATH_SUFFIX)]] = value
            else:
                body_params[key] = value
    return header_params, query_params, path_params, body_params


def apply_default_values(spec_json: str, header_args: Dict, query_args: Dict, path_args: Dict) -> Tuple[Dict, Dict, Dict]:
    """
    Apply default values from the OpenAPI spec to parameters if they are not provided.
    """
    try:
        openapi_spec = load_openapi_spec(spec_json)
        header_params, query_params, path_params, _ = process_openapi_paths(openapi_spec)
        for key, value in header_params.items():
            if (key not in header_args or not header_args[key]) and "default" in value:
                header_args[key] = value.get("default")
        for key, value in query_params.items():
            if (key not in query_args or not query_args[key]) and "default" in value:
                query_args[key] = value.get("default")
        for key, value in path_params.items():
            if (key not in path_args or not path_args[key]) and "default" in value:
                path_args[key] = value.get("default")
    except Exception as e:
        logger.error(f"Failed to apply default values: {e}", exc_info=True)
    return header_args, query_args, path_args


def transform_param_entry(name: str, definition: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a simple parameter definition into a unified structure.
    Excludes keys for description and default if they are empty.
    Includes a 'required' key if the parameter is required.
    """
    entry = {"name": name, "type": definition.get("type", "")}
    if definition.get("description"):
        entry["description"] = definition["description"]
    if "default" in definition and definition["default"] is not None:
        entry["default"] = definition["default"]
    if definition.get("required"):
        entry["required"] = True
    return entry


def transform_body_schema(schema: Any) -> Any:
    """
    Convert a body schema (generated by generate_schema_model) into a dictionary format.
    For object types, the output will include:
      - "type": "object"
      - Optional "description", "default", and "required" keys if available
      - A "properties" key containing child nodes (each transformed recursively)
    For array types, the output includes "type": "array" and an "items" key.
    For other types, outputs the corresponding keys.
    Keys with empty values are omitted.
    """
    if not isinstance(schema, dict):
        return schema

    schema_type = schema.get("type", "")
    result: Dict[str, Any] = {}
    if schema_type:
        result["type"] = schema_type

    if "description" in schema and schema["description"]:
        result["description"] = schema["description"]
    if "default" in schema and schema["default"] is not None:
        result["default"] = schema["default"]
    if "required" in schema and schema["required"]:
        result["required"] = schema["required"]
    if "enum" in schema and schema["enum"]:
        result["enum"] = schema["enum"]

    if schema_type == "object":
        props = schema.get("properties", {})
        if props:
            result["properties"] = {}
            for prop_name, prop_def in props.items():
                result["properties"][prop_name] = transform_body_schema(prop_def)
    elif schema_type == "array":
        if "items" in schema:
            result["items"] = transform_body_schema(schema["items"])
    return result


def extract_endpoints_info(spec_json: str) -> Dict[str, Any]:
    """
    Parse the OpenAPI specification and extract endpoint information:
      - host: extracted from the servers field (empty string if not present)
      - endpoints: a list of endpoints, each containing the path, name (operationId or summary),
        HTTP method, and parameters.
        Parameters are categorized into header, query, and path (each a list of simple parameter definitions)
        and body (transformed using transform_body_schema).
    """
    openapi_spec = load_openapi_spec(spec_json)
    origin = ""
    servers = openapi_spec.get("servers", [])
    if servers and isinstance(servers, list):
        url = servers[0].get("url", "")
        parsed_url = urlparse(url)
        origin = f"{parsed_url.scheme}://{parsed_url.netloc}"

    endpoints = []
    paths = openapi_spec.get("paths", {})
    for path, path_item in paths.items():
        for method, operation in path_item.items():
            if not isinstance(operation, dict):
                continue
            endpoint_info = {
                "path": path,
                "description": operation.get("description") or operation.get("summary") or "",
                "method": method.upper(),
                "name": operation.get("operationId") or operation.get("summary") or ""
            }
            parameters = {
                "header": [],
                "query": [],
                "path": [],
                "body": None
            }
            op_parameters = operation.get("parameters", [])
            h_params, q_params, p_params = parse_parameters(op_parameters)
            for param_name, param_def in h_params.items():
                parameters["header"].append(transform_param_entry(param_name, param_def))
            for param_name, param_def in q_params.items():
                parameters["query"].append(transform_param_entry(param_name, param_def))
            for param_name, param_def in p_params.items():
                parameters["path"].append(transform_param_entry(param_name, param_def))
            request_body = operation.get("requestBody", {})
            if request_body:
                content = request_body.get("content", {})
                body_schema = None
                for content_type, media_obj in content.items():
                    if "schema" in media_obj:
                        body_schema = generate_schema_model(media_obj["schema"])
                        break
                if body_schema:
                    parameters["body"] = transform_body_schema(body_schema)
            endpoint_info["parameters"] = parameters
            endpoints.append(endpoint_info)
    return {"origin": origin, "endpoints": endpoints}


if __name__ == '__main__':
    data = """
{
  "openapi": "3.0.0",
  "info": {
    "title": "Two APIs Example",
    "version": "1.0.0"
  },
  "paths": {
    "/api/example1/{id}": {
      "get": {
        "summary": "Get example1",
        "parameters": [
          {
            "name": "Authorization",
            "in": "header",
            "required": true,
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "X-Custom-Header",
            "in": "header",
            "required": false,
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "integer"
            }
          },
          {
            "name": "filter",
            "in": "query",
            "required": false,
            "schema": {
              "type": "string"
            }
          }
        ],
        "responses": {
          "200": {
            "description": "Successful response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "message": {
                      "type": "string"
                    }
                  }
                }
              }
            }
          }
        }
      }
    },
    "/api/example2/{id}": {
      "post": {
        "summary": "Post example2",
        "parameters": [
          {
            "name": "Authorization",
            "in": "header",
            "required": true,
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "X-Custom-Header",
            "in": "header",
            "required": false,
            "schema": {
              "type": "string"
            }
          },
          {
            "name": "id",
            "in": "path",
            "required": true,
            "schema": {
              "type": "integer"
            }
          }
        ],
        "requestBody": {
          "required": true,
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "items": {
                    "type": "array",
                    "items": {
                      "type": "object",
                      "properties": {
                        "name": {
                          "type": "string"
                        },
                        "email": {
                          "type": "string",
                          "format": "email"
                        },
                        "address": {
                          "type": "object",
                          "properties": {
                            "street": {
                              "type": "string"
                            },
                            "city": {
                              "type": "string"
                            },
                            "zipcode": {
                              "type": "string"
                            }
                          },
                          "required": ["street", "city"]
                        }
                      },
                      "required": ["name", "email"]
                    }
                  },
                  "description": {
                    "type": "string"
                  }
                },
                "required": ["items"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "Successful response",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "status": {
                      "type": "string"
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}

"""

    parameters = extract_endpoints_info(data)

    print(json.dumps(parameters, ensure_ascii=False))
