# Agente de Comparación de Contratos — LegalMove

Este sistema recibe dos imágenes escaneadas (un contrato original y su enmienda), las lee con IA, analiza qué cambió y devuelve un JSON validado con el resultado.

---

## El problema que resuelve

El equipo de Compliance de LegalMove pasa más de 40 horas por semana comparando contratos a mano. Este sistema automatiza ese proceso: en lugar de leer dos documentos y buscar diferencias manualmente, dos agentes de IA hacen el trabajo y devuelven un reporte estructurado listo para usar.

---

## Cómo funciona (el pipeline)

```
Imagen original  →  GPT-4o Vision  →  Texto del contrato
Imagen enmienda  →  GPT-4o Vision  →  Texto de la enmienda
                                            ↓
                                  Agente 1: Contextualización
                                  (mapea la estructura de ambos documentos)
                                            ↓
                                  Agente 2: Extracción de cambios
                                  (detecta qué cambió exactamente)
                                            ↓
                                  Pydantic valida el JSON final
                                            ↓
                                  Langfuse registra todo el proceso
```

---

## Tecnologías usadas y por qué

**GPT-4o Vision** — los contratos llegan como imágenes escaneadas, no como texto. GPT-4o puede leer la imagen y transcribir el contenido preservando la estructura del documento.

**LangChain** — organiza los dos agentes y les pasa la información entre sí de forma ordenada.

**Pydantic** — garantiza que el JSON de salida siempre tenga los campos correctos con los tipos correctos. Si el modelo devuelve algo mal formado, el sistema lo rechaza en lugar de guardar datos incorrectos.

**Langfuse** — registra cada paso del pipeline: qué entró, qué salió, cuántos tokens usó y cuánto tardó. Es la "caja negra" del sistema.

---

## Por qué dos agentes y no uno

El **Agente 1** solo mapea la estructura: qué secciones existen en cada documento y cómo se corresponden entre sí. No extrae cambios.

El **Agente 2** recibe ese mapa y se concentra únicamente en detectar las diferencias. Al dividir el trabajo, cada agente hace una sola cosa y la hace bien. Si fuera un solo agente, tendría que entender la estructura Y extraer cambios al mismo tiempo, lo que genera más errores.

---

## Estructura del proyecto

```
AEM4-Proyecto Final/
├── src/
│   ├── main.py                          → punto de entrada, orquesta el pipeline
│   ├── config.py                        → carga las variables de entorno
│   ├── models.py                        → define cómo debe verse el JSON de salida
│   ├── image_parser.py                  → lee las imágenes con GPT-4o Vision
│   ├── observability.py                 → conexión con Langfuse
│   └── agents/
│       ├── contextualization_agent.py   → Agente 1
│       └── extraction_agent.py          → Agente 2
├── data/test_contracts/                 → 3 pares de contratos de prueba
├── output_samples/                      → JSONs generados por el sistema
├── .env.example                         → plantilla de variables de entorno
└── requirements.txt                     → dependencias con versiones fijadas
```

---

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# completar el .env con las API keys
```

Variables necesarias en el `.env`:

```
OPENAI_API_KEY=...
OPENAI_VISION_MODEL=gpt-4o
OPENAI_AGENT_MODEL=gpt-4o-mini
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

---

## Cómo correrlo

```bash
python src/main.py data/test_contracts/documento_1__original.jpg data/test_contracts/documento_1__enmienda.jpg --output output_samples/case_1.json
```

El sistema imprime el JSON en pantalla y lo guarda en el archivo indicado.

---

## Lo que devuelve

```json
{
  "unidad_de_referencia": {
    "2. Plazo": "Meses",
    "3. Pago": "$"
  },
  "modificacion_validada": true,
  "secciones_modificadas": {
    "2. Plazo": "Se extendió de 12 meses a 24 meses.",
    "6. Confidencialidad": "Sin modificaciones"
  },
  "datos_archivo_original": {
    "plazo": 12,
    "pago": 12000
  },
  "datos_archivo_nuevo": {
    "plazo": 24,
    "pago": 15000
  },
  "resumen": "La enmienda extiende el contrato de 12 a 24 meses y aumenta el pago anual."
}
```

---

## Trazabilidad en Langfuse

Cada ejecución genera una traza con esta jerarquía:

```
contract-analysis
├── parse_original_contract     → GPT-4o lee la imagen original
├── parse_amendment_contract    → GPT-4o lee la imagen de la enmienda
├── contextualization_agent     → Agente 1 mapea la estructura
└── extraction_agent            → Agente 2 extrae los cambios
```

Cada paso registra el input, el output, los tokens utilizados y el tiempo que tardó.

---

## Contratos de prueba incluidos

| Par | Tipo de contrato | Cambios |
|-----|-----------------|---------|
| 1 | Licencia de software | Plazo, pago, soporte, terminación, nueva cláusula de datos |
| 2 | Consultoría | Alcance, duración, honorarios, entregables, nueva cláusula de IP |
| 3 | SaaS | Precio, disponibilidad, soporte |
