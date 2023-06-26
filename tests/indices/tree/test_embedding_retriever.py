"""Test embedding functionalities."""

from collections import defaultdict
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from llama_index.data_structs.node import Node
from llama_index.indices.query.schema import QueryBundle
from llama_index.indices.service_context import ServiceContext
from llama_index.indices.tree.select_leaf_embedding_retriever import (
    TreeSelectLeafEmbeddingRetriever,
)
from llama_index.indices.tree.base import TreeIndex
from llama_index.langchain_helpers.chain_wrapper import (
    LLMMetadata,
    LLMPredictor,
)
from llama_index.langchain_helpers.text_splitter import TokenTextSplitter
from llama_index.readers.schema.base import Document
from tests.mock_utils.mock_prompts import (
    MOCK_INSERT_PROMPT,
    MOCK_SUMMARY_PROMPT,
)
from tests.mock_utils.mock_text_splitter import (
    mock_token_splitter_newline_with_overlaps,
)


@pytest.fixture
def index_kwargs() -> dict:
    """Index kwargs."""
    return {
        "summary_template": MOCK_SUMMARY_PROMPT,
        "insert_prompt": MOCK_INSERT_PROMPT,
        "num_children": 2,
    }


@pytest.fixture
def documents() -> List[Document]:
    """Get documents."""
    # NOTE: one document for now
    doc_text = (
        "Hello world.\n"
        "This is a test.\n"
        "This is another test.\n"
        "This is a test v2."
    )
    return [Document(doc_text)]


def _get_node_text_embedding_similarities(
    query_embedding: List[float], nodes: List[Node]
) -> List[float]:
    """Get node text embedding similarity."""
    text_similarity_map = defaultdict(lambda: 0.0)
    text_similarity_map["Hello world."] = 0.9
    text_similarity_map["This is a test."] = 0.8
    text_similarity_map["This is another test."] = 0.7
    text_similarity_map["This is a test v2."] = 0.6

    similarities = []
    for node in nodes:
        similarities.append(text_similarity_map[node.get_text()])

    return similarities


@patch.object(
    TreeSelectLeafEmbeddingRetriever,
    "_get_query_text_embedding_similarities",
    side_effect=_get_node_text_embedding_similarities,
)
def test_embedding_query(
    _patch_similarity: Any,
    index_kwargs: Dict,
    documents: List[Document],
    mock_service_context: ServiceContext,
) -> None:
    """Test embedding query."""
    tree = TreeIndex.from_documents(
        documents, service_context=mock_service_context, **index_kwargs
    )

    # test embedding query
    query_str = "What is?"
    retriever = tree.as_retriever(retriever_mode="select_leaf_embedding")
    nodes = retriever.retrieve(QueryBundle(query_str))
    assert nodes[0].node.text == "Hello world."


def _mock_tokenizer(text: str) -> int:
    """Mock tokenizer that splits by spaces."""
    return len(text.split(" "))
