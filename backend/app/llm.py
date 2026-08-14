"""Answer generation: retrieved facts → natural reply."""
import os

_SYSTEM = (
    "You are a helpful NYSC assistant for Nigerian corps members. "
    "Answer the user's question using ONLY the facts provided. "
    "If the facts don't fully answer it, say what you don't know. "
    "Be brief and friendly."
)


def generate_answer(question: str, facts: list[str]) -> str:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return _llm_answer(question, facts)
    return _template_answer(facts)


def _template_answer(facts: list[str]) -> str:
    """No-LLM fallback: return the facts themselves, cleanly."""
    if len(facts) == 1:
        return facts[0]
    return "\n".join(f"• {f}" for f in facts)


def _llm_answer(question: str, facts: list[str]) -> str:
    import anthropic
    client = anthropic.Anthropic()
    fact_block = "\n".join(f"- {f}" for f in facts)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",   # cheapest tier — fine for this
        max_tokens=300,
        system=_SYSTEM,
        messages=[{"role": "user",
                   "content": f"Facts:\n{fact_block}\n\nQuestion: {question}"}],
    )
    return msg.content[0].text