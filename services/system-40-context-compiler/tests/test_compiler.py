"""Tests for the context compilation engine."""
from src.models import ContextBlock
from src.services.compiler import ContextCompiler, SOURCE_PRIORITY_MAP
from src.utils.tokens import count_tokens


def test_source_priority_ordering():
    """System prompt should have highest priority."""
    assert SOURCE_PRIORITY_MAP["system_prompt"] < SOURCE_PRIORITY_MAP["qdrant_semantic"]
    assert SOURCE_PRIORITY_MAP["task_description"] < SOURCE_PRIORITY_MAP["past_feedback"]
    assert SOURCE_PRIORITY_MAP["error_context"] < SOURCE_PRIORITY_MAP["conversation_history"]


def test_count_tokens():
    """Token counting should return positive integers for non-empty strings."""
    assert count_tokens("hello world") > 0
    assert count_tokens("") == 0


def test_context_block_model():
    """ContextBlock model should validate correctly."""
    block = ContextBlock(
        source="system_prompt",
        content="You are a developer.",
        token_count=5,
        relevance_score=1.0,
    )
    assert block.source == "system_prompt"
    assert block.relevance_score == 1.0
    assert block.metadata == {}


def test_context_block_metadata():
    """ContextBlock should accept arbitrary metadata."""
    block = ContextBlock(
        source="qdrant_semantic",
        content="test",
        token_count=1,
        relevance_score=0.8,
        metadata={"collection": "kb", "id": "123"},
    )
    assert block.metadata["collection"] == "kb"
