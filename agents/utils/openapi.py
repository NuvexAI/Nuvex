import json
import logging
from typing import Dict, Any

from prance import ResolvingParser

from agents.common.config import SETTINGS

logger = logging.getLogger(__name__)


def validate_openapi(json_str: str):
    try:
        load_openapi_spec(json_str)
        return True, None
    except Exception as e:
        logger.warning(f'check_openapi_spec failed !: {e}', exc_info=True)
        return False, str(e)


def load_openapi_spec(json_str: str) -> Dict[str, Any]:
    try:
        loads = json.loads(json_str)
        fields = fitter_fields(loads)
        json_str = json.dumps(fields, ensure_ascii=False)
    except Exception as e:
        logger.warning(f'fitter_fields failed!: {e}', exc_info=True)
    parser = ResolvingParser(spec_string=json_str, skip_validation=True)
    return parser.specification


def fitter_fields(spec: Dict[str, Any]):
    copy_spec = spec.copy()
    if isinstance(spec, dict):
        for key in spec.keys():
            if key in SETTINGS.OPENAPI_FITTER_FIELDS:
                del copy_spec[key]
            elif isinstance(spec[key], dict):
                copy_spec[key] = fitter_fields(spec[key])
    return copy_spec
