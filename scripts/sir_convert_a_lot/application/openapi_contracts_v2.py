"""OpenAPI component models for Sir Convert-a-Lot service API v2."""

from pydantic import BaseModel

from scripts.sir_convert_a_lot.domain.specs_v2 import JobSpecV2

OPENAPI_CONTRACT_COMPONENT_MODELS: tuple[type[BaseModel], ...] = (JobSpecV2,)
