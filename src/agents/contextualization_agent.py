from __future__ import annotations

from dataclasses import dataclass

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.config import Settings


SYSTEM_PROMPT = """
You are a senior legal analyst.

Your only responsibility is to build a comparison map between an original contract and its amendment.
Do not extract the final changes as JSON.
Do not give a business summary.

Produce a structured contextual map with these sections:
1. Document purpose.
2. Section alignment between original and amendment.
3. Clauses that appear unchanged.
4. Clauses that appear added, removed, or likely modified.
5. Notes about numbering mismatches, renamed sections, or wording changes that may affect extraction.

Be explicit, grounded in the provided text, and avoid hallucinations.
""".strip()

HUMAN_PROMPT = """
Build the contextual map for these two documents.

ORIGINAL CONTRACT
-----------------
{original_text}

AMENDMENT / UPDATED CONTRACT
----------------------------
{amendment_text}
""".strip()


@dataclass
class AgentResult:
    content: str
    usage: dict[str, int] | None


class ContextualizationAgent:
    def __init__(self, settings: Settings) -> None:
        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                ("human", HUMAN_PROMPT),
            ]
        )
        self.llm = ChatOpenAI(
            model=settings.openai_agent_model,
            api_key=settings.openai_api_key,
            temperature=0,
        )

    def run(self, original_text: str, amendment_text: str) -> AgentResult:
        chain = self.prompt | self.llm
        response = chain.invoke(
            {
                "original_text": original_text,
                "amendment_text": amendment_text,
            }
        )

        usage = getattr(response, "usage_metadata", None)
        content = response.content if isinstance(response.content, str) else str(response.content)

        return AgentResult(content=content.strip(), usage=usage)