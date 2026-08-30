"""Create-job multipart part-name discovery for Service API v2.

Purpose:
    Provide form-part names to route-specific create-job validators without
    replaying multipart parsing after FastAPI has already bound upload fields.

Relationships:
    - Used by `interfaces.http_routes_jobs_v2` during job admission.
"""

from __future__ import annotations

from fastapi import Request, UploadFile
from starlette.datastructures import FormData


def bound_create_job_form_part_names_v2(
    *,
    request: Request,
    resources: UploadFile | None,
    reference_docx: UploadFile | None,
) -> frozenset[str]:
    """Return submitted create-job multipart field names without parsing again."""

    cached_form = getattr(request, "_form", None)
    if isinstance(cached_form, FormData):
        return frozenset(str(key) for key in cached_form.keys())

    names = {"file", "job_spec"}
    if resources is not None:
        names.add("resources")
    if reference_docx is not None:
        names.add("reference_docx")
    return frozenset(names)
