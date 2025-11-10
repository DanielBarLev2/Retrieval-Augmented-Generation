"""
Wrapper around SentenceTransformers to produce normalized embeddings.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Iterable, Sequence, TYPE_CHECKING, overload

import numpy as np

from app.core.settings import get_settings

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


@lru_cache(maxsize=1)
def get_embedding_model() -> "SentenceTransformer":
    """
    Load and cache the SentenceTransformers embedding model.

    The model name comes from the `EMBED_MODEL` setting. We validate that the
    embedding dimensionality matches the configured vector size to guard against
    runtime mismatches with Qdrant.
    """
    settings = get_settings()
    model_name = settings.embed_model

    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)

    expected_dimension = settings.vector_size
    actual_dimension = model.get_sentence_embedding_dimension()
    if actual_dimension != expected_dimension:
        raise ValueError(
            "Embedding dimension mismatch between model and configuration: "
            f"expected {expected_dimension}, got {actual_dimension} for model "
            f"{model_name}.")

    return model


def _normalize(vectors: np.ndarray) -> np.ndarray:
    """
    L2-normalize the embeddings. Avoid division by zero by leaving zero vectors unchanged.
    """
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    # Replace zeros with ones to avoid division errors; zero vectors remain zero.
    norms[norms == 0.0] = 1.0
    return vectors / norms


@overload
def encode(texts: str, *, normalize: bool = True, batch_size: int = 32) -> np.ndarray: ...


@overload
def encode(texts: Sequence[str], *, normalize: bool = True, batch_size: int = 32) -> np.ndarray: ...


def encode(texts: str | Sequence[str],
           *,
           normalize: bool = True,
           batch_size: int = 32) -> np.ndarray:
    """
    Convert text or a batch of texts into embeddings.

    Parameters
    ----------
    texts:
        Either a single string or a sequence of strings to encode.
    normalize:
        Whether to L2-normalize the returned embeddings.
    batch_size:
        Forwarded to SentenceTransformers. Controls the encode batch size.
    """
    model = get_embedding_model()

    # Convert single text to sequence for consistent processing
    is_single_text = isinstance(texts, str)
    inputs: Iterable[str]
    if is_single_text:
        inputs = [texts]
    else:
        inputs = texts

    embeddings = model.encode(
        inputs,
        batch_size=batch_size,
        convert_to_numpy=True,
        show_progress_bar=False,
        normalize_embeddings=False,
    )

    if normalize:
        embeddings = _normalize(embeddings)

    if is_single_text:
        return embeddings[0]
    return embeddings


def embed_query(query: str) -> list[float]:
    """
    Convenience helper for single-query embedding.
    """
    return encode(query).tolist()


def embed_documents(documents: Sequence[str], *, batch_size: int = 32) -> list[list[float]]:
    """
    Encode a batch of documents into embeddings.
    """
    embeddings = encode(documents, batch_size=batch_size)
    return embeddings.tolist()

