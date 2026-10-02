from app.services.prompt_builder import PromptBuilder
from app.services.context_assembler import AssembledContext


def test_system_prompt_has_rules():
    assert "Facts-only" in PromptBuilder.SYSTEM_PROMPT or "facts" in PromptBuilder.SYSTEM_PROMPT
    assert "Source" in PromptBuilder.SYSTEM_PROMPT


def test_build_messages():
    ctx = AssembledContext(context_text="hello", sources=[], total_tokens=5, chunk_count=1)
    messages = PromptBuilder().build("q?", ctx)
    assert messages[0]["role"] == "system"
    assert "CONTEXT" in messages[1]["content"]
