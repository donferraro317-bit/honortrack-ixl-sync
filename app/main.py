from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from pathlib import Path
from threading import Thread
from datetime import datetime

from app.jobs import create_job, update_job, append_log, recent_jobs
from app.worker import auth_file_exists, run_test_one, run_export_sample

STATIC_DIR = Path("static")
HTML_FILE = STATIC_DIR / "ixl_sync_starter.html"

app = FastAPI(title="HonorTrack IXL Sync Starter")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TestOneRequest(BaseModel):
    teacher_id: str | None = None
    score_url: str


class ExportSampleRequest(BaseModel):
    teacher_id: str
    limit: int = Field(default=5, ge=1, le=25)


@app.get("/")
def home():
    return FileResponse(HTML_FILE)


@app.get("/api/ixl/health")
def health():
    jobs = recent_jobs(10)
    return {
        "status": "ok",
        "session": "connected" if auth_file_exists() else "missing",
        "queue": "idle",
        "last_job": jobs[0]["job_type"] if jobs else None,
        "files_exported": sum(len(j.get("exports", [])) for j in jobs),
        "failures": sum(int(j.get("failures", 0)) for j in jobs),
    }


@app.post("/api/ixl/connect")
def connect_ixl():
    raise HTTPException(
        status_code=501,
        detail="Hosted IXL connect flow not implemented yet. Upload a valid auth/ixl_state.json file for now."
    )


@app.post("/api/ixl/test-one")
def test_one(req: TestOneRequest):
    job = create_job("test-one", req.model_dump())

    def runner():
        try:
            update_job(job["id"], status="running", started_at=datetime.utcnow().isoformat())
            append_log(job["id"], "Starting test-one export.")
            result = run_test_one(req.score_url)
            append_log(job["id"], f"Saved {result['file_name']}")
            update_job(
                job["id"],
                status="success",
                completed_at=datetime.utcnow().isoformat(),
                exports=[result],
            )
        except Exception as exc:
            append_log(job["id"], f"Failed: {exc}")
            update_job(
                job["id"],
                status="failed",
                completed_at=datetime.utcnow().isoformat(),
                failures=1,
            )

    Thread(target=runner, daemon=True).start()
    return {"message": "Test-one job queued.", "job_id": job["id"]}


@app.post("/api/ixl/export-sample")
def export_sample(req: ExportSampleRequest):
    job = create_job("export-sample", req.model_dump())

    def runner():
        try:
            update_job(job["id"], status="running", started_at=datetime.utcnow().isoformat())
            append_log(job["id"], f"Starting export sample for teacher {req.teacher_id}")
            exports = run_export_sample(req.teacher_id, req.limit)
            append_log(job["id"], f"Exported {len(exports)} file(s)")
            update_job(
                job["id"],
                status="success",
                completed_at=datetime.utcnow().isoformat(),
                exports=exports,
            )
        except Exception as exc:
            append_log(job["id"], f"Failed: {exc}")
            update_job(
                job["id"],
                status="failed",
                completed_at=datetime.utcnow().isoformat(),
                failures=1,
            )

    Thread(target=runner, daemon=True).start()
    return {"message": "Export-sample job queued.", "job_id": job["id"]}


@app.get("/api/ixl/jobs/recent")
def jobs_recent():
    return {
        "auth": "connected" if auth_file_exists() else "missing",
        "jobs": recent_jobs(10),
    }
