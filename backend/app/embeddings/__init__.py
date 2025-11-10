"""
Convenience exports for working with the shared embedding model.
"""

from .model import (
    embed_documents,
    embed_query,
    encode,
    get_embedding_model,
)

__all__ = [
    "embed_documents",
    "embed_query",
    "encode",
    "get_embedding_model",
]

