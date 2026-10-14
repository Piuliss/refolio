"""JSON Schema export and validation for DocumentIR."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
from pydantic import TypeAdapter

from converter.ir.models import DocumentIR

_ADAPTER = TypeAdapter(DocumentIR)


def ir_json_schema() -> dict[str, Any]:
    return _ADAPTER.json_schema()


def validate_ir_document(data: dict[str, Any]) -> DocumentIR:
    schema = ir_json_schema()
    jsonschema.validate(instance=data, schema=schema)
    return DocumentIR.model_validate(data)


def dump_schema(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ir_json_schema(), indent=2) + "\n", encoding="utf-8")
