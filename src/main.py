from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from openai import OpenAI
from pydantic import ValidationError


if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.agents.contextualization_agent import ContextualizationAgent
from src.agents.extraction_agent import ExtractionAgent
from src.config import load_settings
from src.image_parser import parse_contract_image
from src.models import ContractChangeOutput
from src.observability import ObservabilityManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare an original contract image against its amendment image."
    )
    parser.add_argument("original_image", help="Path to the original contract image")
    parser.add_argument("amendment_image", help="Path to the amendment or updated contract image")
    parser.add_argument(
        "--output",
        default="output_samples/latest_output.json",
        help="Path where the validated JSON result will be stored",
    )
    return parser.parse_args()


def clean_json_payload(raw_text: str) -> str:
    cleaned = raw_text.strip()

    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    if cleaned.startswith("{") and cleaned.endswith("}"):
        return cleaned

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        raise ValueError("The extraction agent did not return a JSON object.")

    return match.group(0)


def write_output(output_path: str | Path, result: ContractChangeOutput) -> Path:
    destination = Path(output_path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return destination


def run_pipeline(original_image: str, amendment_image: str, output_path: str | Path) -> ContractChangeOutput:
    settings = load_settings()
    observability = ObservabilityManager(settings)

    openai_client = OpenAI(api_key=settings.openai_api_key)
    contextualization_agent = ContextualizationAgent(settings)
    extraction_agent = ExtractionAgent(settings)

    try:
        with observability.span("contract-analysis") as root_span:
            root_span.update(
                input={
                    "original_image": original_image,
                    "amendment_image": amendment_image,
                    "output_path": str(output_path),
                },
                metadata={
                    "vision_model": settings.openai_vision_model,
                    "agent_model": settings.openai_agent_model,
                    "langfuse_enabled": settings.langfuse_enabled,
                },
            )

            with observability.span("parse_original_contract") as span:
                span.update(input={"image_path": original_image})
                original_text, original_usage = parse_contract_image(
                    original_image, openai_client, settings.openai_vision_model
                )
                span.update(
                    output=original_text,
                    metadata={"usage": original_usage, "characters": len(original_text)},
                )

            with observability.span("parse_amendment_contract") as span:
                span.update(input={"image_path": amendment_image})
                amendment_text, amendment_usage = parse_contract_image(
                    amendment_image, openai_client, settings.openai_vision_model
                )
                span.update(
                    output=amendment_text,
                    metadata={"usage": amendment_usage, "characters": len(amendment_text)},
                )

            with observability.span("contextualization_agent") as span:
                span.update(
                    input={
                        "original_text": original_text,
                        "amendment_text": amendment_text,
                    }
                )
                contextual_result = contextualization_agent.run(
                    original_text=original_text,
                    amendment_text=amendment_text,
                )
                span.update(
                    output=contextual_result.content,
                    metadata={"usage": contextual_result.usage},
                )

            with observability.span("extraction_agent") as span:
                span.update(
                    input={
                        "contextual_map": contextual_result.content,
                        "original_text": original_text,
                        "amendment_text": amendment_text,
                    }
                )
                extraction_result = extraction_agent.run(
                    contextual_map=contextual_result.content,
                    original_text=original_text,
                    amendment_text=amendment_text,
                )
                validated_result = ContractChangeOutput.model_validate_json(
                    clean_json_payload(extraction_result.content)
                )
                span.update(
                    output=validated_result.model_dump(),
                    metadata={"usage": extraction_result.usage},
                )

            destination = write_output(output_path, validated_result)
            root_span.update(output=validated_result.model_dump(), metadata={"saved_to": str(destination)})
            return validated_result
    finally:
        observability.flush()


def main() -> int:
    args = parse_args()

    try:
        result = run_pipeline(
            original_image=args.original_image,
            amendment_image=args.amendment_image,
            output_path=args.output,
        )
    except ValidationError as exc:
        print("Validation error while building the final JSON output:", file=sys.stderr)
        print(exc, file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Pipeline execution failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())