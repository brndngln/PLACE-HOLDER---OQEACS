"""Tests for effectiveness tracking models."""
from src.models import EffectivenessReport, BlockEffectiveness


def test_effectiveness_report_model():
    report = EffectivenessReport(
        task_id="task-1",
        context_hash="abc123",
        output_quality_score=0.85,
        task_success=True,
        feedback="Good context selection",
    )
    assert report.task_success is True
    assert report.output_quality_score == 0.85


def test_block_effectiveness_model():
    be = BlockEffectiveness(
        source="qdrant_semantic",
        avg_quality=0.82,
        usage_count=150,
        success_rate=0.91,
    )
    assert be.usage_count == 150
    assert be.success_rate == 0.91
