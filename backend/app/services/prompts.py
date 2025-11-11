"""
Utilities to assemble retrieval-augmented prompts for LLM generation.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


DEFAULT_SYSTEM_PROMPT = (
    "You are a knowledgeable assistant that prioritizes answering user questions using "
    "the provided context. When the context does not contain the needed details, draw "
    "on your broader expertise to offer a clear, accurate answer and optionally mention "
    "that the response is based on general knowledge."
)


@dataclass(slots=True)
class ChatTurn:
    """
    Representation of a previous exchange in the conversation history.
    """

    role: str
    content: str

    def formatted(self) -> str:
        return f"{self.role.capitalize()}: {self.content.strip()}"


class PromptBuilder:
    """
    Build prompts that weave together system instructions, retrieved context, and user queries.
    """

    def __init__(
        self,
        *,
        system_prompt: str | None = None,
        answer_instructions: str | None = None,
        general_knowledge_instructions: str | None = None,
    ):
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT
        self.answer_instructions = (
            answer_instructions
            or "Provide a concise, factual answer grounded in the relevant context. Ignore any snippets that do not relate to the user question."
        )
        self.general_knowledge_instructions = (
            general_knowledge_instructions
            or "No supporting context was retrieved for this question. Provide a concise, factual answer based on your general knowledge and note that no sources are available."
        )

    @staticmethod
    def _format_context(contexts: Sequence[str]) -> str:
        lines = []
        for idx, snippet in enumerate(contexts, start=1):
            lines.append(f"Context {idx}:\n{snippet.strip()}")
        return "\n\n".join(lines)

    @staticmethod
    def _format_history(history: Iterable[ChatTurn]) -> str:
        return "\n".join(turn.formatted() for turn in history)

    def build_prompt(
        self,
        *,
        question: str,
        contexts: Sequence[str],
        history: Sequence[ChatTurn] | None = None,
        general_knowledge: bool = False,
    ) -> str:
        """
        Produce a single prompt string suitable for Ollama's generate endpoint.
        """
        sections = [f"System:\n{self.system_prompt}"]

        if history:
            formatted_history = self._format_history(history)
            if formatted_history:
                sections.append(f"Conversation History:\n{formatted_history}")

        if contexts:
            sections.append(f"Retrieved Context:\n{self._format_context(contexts)}")

        instructions = (
            self.general_knowledge_instructions if general_knowledge or not contexts else self.answer_instructions
        )
        sections.append(f"Instructions:\n{instructions}")
        sections.append(f"User Question:\n{question.strip()}")
        sections.append("Answer:")

        return "\n\n".join(sections)

