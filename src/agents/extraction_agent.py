from __future__ import annotations

import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.agents.contextualization_agent import AgentResult
from src.config import Settings
from src.models import ContractChangeOutput


SYSTEM_PROMPT = """
Eres un auditor de cambios contractuales.

Tu única responsabilidad es identificar las diferencias exactas entre el contrato original y su enmienda.
Debes distinguir entre adiciones, eliminaciones y modificaciones.
Cada conclusión debe estar fundamentada en los textos provistos y el mapa contextual.

Devuelve únicamente un JSON válido que cumpla este esquema:
{schema}

Reglas estrictas:

unidad_de_referencia:
- Diccionario con las mismas claves que secciones_modificadas.
- El valor es una referencia corta que describe el tipo de dato principal de esa sección.
- No es una unidad de medida, sino una referencia de contexto. Ejemplos:
  "Texto" → cláusulas o descripciones narrativas
  "Meses" → plazos expresados en meses
  "Días"  → plazos expresados en días
  "$"     → montos monetarios
  "%"     → porcentajes
  "Fecha" → fechas
- Usa el criterio que mejor refleje la naturaleza del dato de cada sección.

secciones_modificadas:
- Diccionario que incluye TODAS las secciones del contrato, no solo las que cambiaron.
- La clave es el nombre exacto de la sección. El valor describe qué cambió.
- Si una sección no tuvo cambios, el valor debe ser exactamente: "Sin modificaciones".
- Si hubo un cambio, describe con precisión qué decía antes y qué dice ahora.
- Ejemplo correcto:
  "2. Plazo": "Se extendió de 12 meses a 24 meses.",
  "6. Confidencialidad": "Sin modificaciones"

datos_archivo_original y datos_archivo_nuevo:
- Deben tener exactamente una clave por cada sección que aparece en secciones_modificadas.
- La clave es el nombre de la sección convertido a snake_case sin números ni puntos (ej: "1. Plazo" → "plazo", "3. Pago" → "pago").
- El valor es el contenido real de esa sección en cada documento.
- Si el valor es numérico (meses, montos, días, porcentajes): número JSON sin comillas.
  Correcto:   "plazo": 12,  "pago": 12000,  "terminacion": 30
  Incorrecto: "plazo": "12 meses",  "pago": "USD 12.000"
- Si el valor es texto (una cláusula, una descripción): string con el contenido de esa sección.
- Si una sección fue AGREGADA por la enmienda (no existía en el original): en datos_archivo_original su valor es null.
- Si una sección fue ELIMINADA por la enmienda: en datos_archivo_nuevo su valor es null.
- Si un dato no cambió, repite el mismo valor en ambos diccionarios.
- CRÍTICO — fechas: formato DD/MM/YYYY.
  Correcto: "fecha_inicio": "01/03/2024"

resumen:
- Descripción clara y detallada de todos los cambios introducidos por la enmienda, en español.
- Omite cambios puramente cosméticos que no alteren el significado legal.

No envuelvas el JSON en bloques de markdown.
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