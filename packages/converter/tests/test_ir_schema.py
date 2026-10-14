from __future__ import annotations

from converter.ir.models import DocumentIR, DocumentMetadata
from converter.ir.schema import validate_ir_document


def test_ir_roundtrip_schema() -> None:
    doc = DocumentIR(metadata=DocumentMetadata(title="T", language="es"))
    data = doc.model_dump(mode="json")
    restored = validate_ir_document(data)
    assert restored.metadata.title == "T"
