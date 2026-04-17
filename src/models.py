from __future__ import annotations

from typing import Dict, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class ContractChangeOutput(BaseModel):
    unidad_de_referencia: Dict[str, str] = Field(
        ...,
        description=(
            "Diccionario con una clave por sección que indica el tipo o referencia del dato principal "
            "de esa sección. Ejemplos: 'Texto', 'Meses', '$', '%', 'Días', 'Fecha'."
        ),
    )
    modificacion_validada: bool = Field(
        default=False,
        description=(
            "true si se detectaron cambios entre el contrato original y la enmienda. "
            "false si todos los campos son 'Sin modificaciones'."
        ),
    )
    secciones_modificadas: Dict[str, str] = Field(
        ...,
        description=(
            "Diccionario donde cada clave es el nombre de una sección del contrato "
            "y el valor describe qué cambió, o 'Sin modificaciones' si no hubo cambios."
        ),
    )
    datos_archivo_original: Dict[str, Union[int, float, str, None]] = Field(
        ...,
        description=(
            "Datos clave del contrato original. "
            "Valores numéricos sin comillas. Fechas en formato DD/MM/YYYY."
        ),
    )
    datos_archivo_nuevo: Dict[str, Union[int, float, str, None]] = Field(
        ...,
        description=(
            "Datos clave del contrato modificado, mismas claves que datos_archivo_original. "
            "Valores numéricos sin comillas. Fechas en formato DD/MM/YYYY."
        ),
    )
    resumen: str = Field(
        ...,
        min_length=20,
        description="Descripción detallada de todos los cambios introducidos por la enmienda.",
    )

    @model_validator(mode="after")
    def compute_modificacion_validada(self) -> "ContractChangeOutput":
        """Deriva modificacion_validada desde secciones_modificadas, sin depender del LLM."""
        self.modificacion_validada = any(
            v.strip().lower() != "sin modificaciones"
            for v in self.secciones_modificadas.values()
        )
        return self

    @field_validator("datos_archivo_original", "datos_archivo_nuevo", mode="before")
    @classmethod
    def coerce_numeric_strings(cls, value: dict) -> dict:
        """Convierte strings numéricos a int o float para garantizar tipos correctos en el JSON."""
        if not isinstance(value, dict):
            raise TypeError("Se esperaba un diccionario")

        result: dict = {}
        for key, val in value.items():
            if isinstance(val, str):
                stripped = val.strip()
                try:
                    result[key] = int(stripped)
                    continue
                except ValueError:
                    pass
                try:
                    result[key] = float(stripped)
                    continue
                except ValueError:
                    pass
            result[key] = val

        return result

    @field_validator("resumen")
    @classmethod
    def clean_resumen(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 20:
            raise ValueError("El resumen es demasiado corto")
        return cleaned
