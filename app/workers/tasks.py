from app.workers.celery_app import celery_app
from app.import_engine.pipeline import run_import_job


@celery_app.task
def process_import(job_id: str):
    run_import_job(job_id)