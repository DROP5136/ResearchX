"""Document processing routes for the AI service."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import require_internal_token
from app.api.schemas.documents import (
    DocumentDeleteRequest,
    DocumentDeleteResponse,
    DocumentProcessRequest,
    DocumentProcessResponse,
)
from app.api.services.document_service import DocumentService

router = APIRouter(
    prefix="/api/v1/documents",
    tags=["documents"],
    dependencies=[Depends(require_internal_token)],
)
_service = DocumentService()


@router.post("/process", response_model=DocumentProcessResponse)
def process_document(body: DocumentProcessRequest) -> DocumentProcessResponse:
    result = _service.process(body)
    return DocumentProcessResponse(**result)


@router.post("/delete", response_model=DocumentDeleteResponse)
def delete_document(body: DocumentDeleteRequest) -> DocumentDeleteResponse:
    result = _service.delete(body.document_id)
    return DocumentDeleteResponse(**result)
