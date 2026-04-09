from __future__ import annotations

import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.agents.contextualization_agent import AgentResult
from src.config import Settings
from src.models import ContractChangeOutput


SYSTEM_PROMPT = """
You are a legal change auditor.

Your only responsibility is to identify the exact contractual differences between the original agreement and the amendment.
You must distinguish among additions, deletions, and modifications.
You must ground every conclusion in the provided text and contextual map.

Return only valid JSON matching this schema:
{schema}

Rules:
- sections_changed must contain the clause titles or identifiers that changed.
- topics_touched must describe legal or commercial topics affected by those changes.
- summary_of_the_change must explain the concrete differences introduced by the amendment.
- Ignore purely cosmetic changes unless they alter legal meaning.
- Do not wrap the JSON in markdown fences.
""".strip()

HUMAN_PROMPT = """
Use the contextual map and both source texts to extract the final changes.

CONTEXTUAL MAP
--------------
{contextual_map}

ORIGINAL CONTRACT
-----------------
{original_text}

AMENDMENT / UPDATED CONTRACT
----------------------------
{amendment_text}
""".strip()


class ExtractionAgent:
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

    def run(
        self,
        contextual_map: str,
        original_text: str,
        amendment_text: str,
    ) -> AgentResult:
        chain = self.prompt | self.llm
        response = chain.invoke(
            {
                "schema": json.dumps(ContractChangeOutput.model_json_schema(), indent=2),
                "contextual_map": contextual_map,
                "original_text": original_text,
                "amendment_text": amendment_text,
            }
        )

        usage = getattr(response, "usage_metadata", None)
        content = response.content if isinstance(response.content, str) else str(response.content)

        return AgentResult(content=content.strip(), usage=usage)