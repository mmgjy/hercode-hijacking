"""Source adapters.

An adapter turns a fetched document (HTML/JSON text) into a list of raw signal
dicts. Adapters are selected by ``adapter_key`` in the source-set / retailer
configuration, so new sources are added via config + (optionally) a small
adapter class — never by editing the pipeline.
"""
from app.adapters.base import ADAPTER_REGISTRY, Adapter, get_adapter
from app.adapters import (  # noqa: F401  register adapters on import
    generic_jsonld,
    configurable_listing,
    global_retailer,
    global_corroborating_source,
    swiss_retailer,
)

__all__ = ["ADAPTER_REGISTRY", "Adapter", "get_adapter"]
