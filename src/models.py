from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field, field_validator


class ContractChangeOutput(BaseModel):
    sections_changed: List[str] = Field(
        ...,
        min_length=1,
        description="Identifiers or titles of the contract sections that changed.",
    )
    topics_touched: List[str] = Field(
        ...,
        min_length=1,
        description="Legal or commercial topics affected by the amendment.",
    )
    summary_of_the_change: str = Field(
        ...,
        min_length=20,
        description="Detailed but concise explanation of the differences.",
    )

    @field_validator("sections_changed", "topics_touched", mode="before")
    @classmethod
    def clean_string_lists(cls, value: List[str]) -> List[str]:
        if not isinstance(value, list):
            raise TypeError("Expected a list of strings")

        cleaned: list[str] = []
        for item in value:
            text = str(item).strip()
            if text and text not in cleaned:
                cleaned.append(text)

        if not cleaned:
            raise ValueError("List cannot be empty after normalization")

        return cleaned

    @field_validator("summary_of_the_change")
    @classmethod
    def clean_summary(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 20:
            raise ValueError("summary_of_the_change is too short")
        return cleaned