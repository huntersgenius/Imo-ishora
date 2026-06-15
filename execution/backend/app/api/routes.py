"""FastAPI route definitions (web edge).

Routes coordinate services via the container; they contain no dictionary,
R2, or video logic. Background processing is launched with FastAPI's
BackgroundTasks so the synthesis endpoint returns immediately after the job is
queued, per Part 03.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import JSONResponse

from ..core.container import Container
from ..schemas.synthesis import HealthResponse, JobResponse, SynthesisRequest
from ..services.errors import SynthesisError
from ..services.jobs import JobStatus
from ..services.presentation import job_to_dict

router = APIRouter()


def _container(request: Request) -> Container:
    return request.app.state.container


@router.get("/health", response_model=HealthResponse, tags=["ops"])
def health(request: Request) -> HealthResponse:
    c = _container(request)
    return HealthResponse(
        status="ok",
        app_name=c.settings.app_name,
        environment=c.settings.environment,
        dictionary_entries=c.dictionary.size,
        playable_clips=c.playable_clip_count,
        r2_configured=c.r2.is_configured,
    )


@router.post("/synthesize", response_model=JobResponse, tags=["synthesis"])
async def synthesize(
    payload: SynthesisRequest, request: Request, background: BackgroundTasks
) -> JSONResponse:
    c = _container(request)
    try:
        record = c.synthesis.create_job(payload.text)
    except SynthesisError as err:
        # Structured, user-safe error. Internal detail stays in logs.
        return JSONResponse(
            status_code=422 if err.code.value == "input_validation" else 200,
            content={
                "error_code": err.code.value,
                "error_message": err.user_message,
            },
        )

    # Launch background processing without blocking the response.
    background.add_task(c.synthesis.run_job, record.job_id)
    return JSONResponse(status_code=202, content=job_to_dict(record))


@router.get("/jobs/{job_id}", response_model=JobResponse, tags=["synthesis"])
def job_status(job_id: str, request: Request) -> JSONResponse:
    c = _container(request)
    record = c.jobs.get(job_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "unknown_job", "error_message": "Job topilmadi."},
        )
    return JSONResponse(status_code=200, content=job_to_dict(record))


__all__ = ["router"]
