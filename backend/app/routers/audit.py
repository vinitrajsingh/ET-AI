"""
Audit endpoints.

  GET /audit/preview?scope=...   the structured audit data as JSON (UI preview)
  GET /audit/package?scope=...   the same data rendered as a downloadable PDF

scope is "fleet" or a specific equipment tag. Assembly and rendering both live in
services; this router just wires them to HTTP.
"""

from fastapi import APIRouter, Response

from app.services.audit_service import AuditPackage, build_audit_package
from app.services.pdf_service import render_audit_pdf

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/preview", response_model=AuditPackage)
def preview(scope: str = "fleet") -> AuditPackage:
    return build_audit_package(scope)


@router.get("/package")
def package(scope: str = "fleet") -> Response:
    pdf = render_audit_pdf(build_audit_package(scope))
    filename = f"audit_package_{scope}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
