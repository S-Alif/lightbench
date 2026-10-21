"""every api url in one place."""
from __future__ import annotations

from starlette.routing import Route

from .routes.files import item_file, item_thumb, job_zip
from .routes.jobs import cancel_job, create_job, delete_job, edit_result, get_job, list_jobs, open_folder
from .routes.models import list_models
from .routes.system import system

api_routes = [
    Route("/api/system", system),
    Route("/api/models", list_models),
    Route("/api/jobs", list_jobs),
    Route("/api/jobs", create_job, methods=["POST"]),
    Route("/api/jobs/{job_id}", get_job),
    Route("/api/jobs/{job_id}", delete_job, methods=["DELETE"]),
    Route("/api/jobs/{job_id}/cancel", cancel_job, methods=["POST"]),
    Route("/api/jobs/{job_id}/zip", job_zip),
    Route("/api/jobs/{job_id}/open-folder", open_folder, methods=["POST"]),
    Route("/api/jobs/{job_id}/items/{item_id}/edit", edit_result, methods=["POST"]),
    Route("/api/jobs/{job_id}/items/{item_id}/thumb", item_thumb),
    Route("/api/jobs/{job_id}/items/{item_id}/file", item_file),
]
