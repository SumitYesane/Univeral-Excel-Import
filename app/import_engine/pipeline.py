import logging

from app.core.config import settings
from app.core.rate_limit import get_semaphore
from app.import_engine.services.bulk_insert_service import bulk_insert_rows
from app.import_engine.services.duplicate_service import filter_db_duplicates, filter_file_duplicates
from app.import_engine.services.error_file_service import build_error_file
from app.import_engine.services.job_tracker import JobTracker
from app.import_engine.services.lock_service import acquire_lock
from app.import_engine.services.mapping_service import build_column_mapping, map_columns
from app.import_engine.services.parser_service import SOURCE_ROW_FIELD, SOURCE_SHEET_FIELD, parse_file
from app.import_engine.services.relationship_service import build_relationships
from app.import_engine.services.storage_service import StorageService
from app.import_engine.services.transform_service import apply_transforms
from app.import_engine.services.validation_service import validate_rows
from app.utils.exceptions import ImportException

logger = logging.getLogger(__name__)


def _cap_errors(errors):
    return errors[: settings.MAX_ERRORS_PER_JOB]


def _build_source_row_lookup(chunk):
    data_columns = [column for column in chunk.columns if column not in {SOURCE_ROW_FIELD, SOURCE_SHEET_FIELD}]
    lookup = {}
    for _, row in chunk.iterrows():
        row_dict = row.to_dict()
        source_row = row_dict.get(SOURCE_ROW_FIELD)
        lookup[source_row] = {
            **{column: row_dict.get(column) for column in data_columns},
            SOURCE_ROW_FIELD: source_row,
            SOURCE_SHEET_FIELD: row_dict.get(SOURCE_SHEET_FIELD),
        }
    return lookup


def _project_errors_to_source_rows(error_entries, source_row_lookup):
    projected = []
    for entry in error_entries:
        source_row = entry.get("row")
        original_data = source_row_lookup.get(source_row)
        if original_data:
            entry = {**entry, "data": original_data}
        projected.append(entry)
    return projected


def run_import_job(job_id: str) -> None:
    job_tracker = JobTracker()
    job = job_tracker.get_job(job_id)
    if not job:
        return

    sem = get_semaphore(job.tenant_id)
    acquired = sem.acquire(blocking=False)
    if not acquired:
        job_tracker.update_status(job_id, "queued")
        sem.acquire()

    try:
        job_tracker.update_status(job_id, "running")
        storage = StorageService()
        local_path = storage.download_to_local(job.file_url, job.tenant_id)

        total_rows = 0
        success_rows = 0
        failed_rows = 0
        errors = []

        from app.import_engine.models.model_definitions import ModelDefinition

        model_definitions = [ModelDefinition(**m) for m in job.model_definitions] if isinstance(job.model_definitions, list) else []
        model_lookup = {model.name: model for model in model_definitions}
        sheet_mapping = job.sheet_mapping or {}
        first_sheet_used = False

        for sheet_name, chunk in parse_file(local_path):
            source_row_lookup = _build_source_row_lookup(chunk)
            models_for_sheet = sheet_mapping.get(sheet_name)
            if not models_for_sheet and not sheet_mapping and not first_sheet_used:
                models_for_sheet = [model.name for model in model_definitions]
                first_sheet_used = True

            if not models_for_sheet:
                continue

            for model_name in models_for_sheet:
                model_def = model_lookup.get(model_name)
                if not model_def:
                    continue

                extra_fields = [rule.source for rule in model_def.transformations if rule.source]
                column_mapping = build_column_mapping(chunk.columns, model_def, extra_fields=extra_fields)
                mapped = map_columns(chunk, column_mapping)
                transformed = apply_transforms(mapped, model_def.transformations)

                for field in model_def.field_names():
                    if field not in transformed.columns:
                        transformed[field] = None

                metadata_fields = [field for field in (SOURCE_ROW_FIELD, SOURCE_SHEET_FIELD) if field in transformed.columns]
                transformed = transformed[model_def.field_names() + metadata_fields]
                total_rows += len(transformed)

                filtered_df, file_dupes = filter_file_duplicates(transformed, model_def.unique_fields(), model_def.name)
                errors.extend(_project_errors_to_source_rows(file_dupes, source_row_lookup))
                failed_rows += len(file_dupes)

                valid_rows, row_errors = validate_rows(filtered_df, model_def)
                errors.extend(_project_errors_to_source_rows(row_errors, source_row_lookup))
                failed_rows += len(row_errors)

                valid_rows, db_dupes = filter_db_duplicates(
                    job.db_connection,
                    model_def.table,
                    valid_rows,
                    model_def.unique_fields(),
                    model_def.name,
                )
                errors.extend(_project_errors_to_source_rows(db_dupes, source_row_lookup))
                failed_rows += len(db_dupes)

                related_rows = build_relationships(job.db_connection, model_def, valid_rows)

                if model_def.lock_table:
                    lock_key = f"lock:import:{job.tenant_id}:{model_def.table}"
                    with acquire_lock(lock_key):
                        inserted = bulk_insert_rows(job.db_connection, model_def.table, related_rows)
                else:
                    inserted = bulk_insert_rows(job.db_connection, model_def.table, related_rows)

                success_rows += inserted
                job_tracker.update_progress(job_id, total_rows, success_rows, failed_rows)

        error_url = None
        if errors:
            error_path = build_error_file(_cap_errors(errors), job_id)
            error_url = storage.upload_error_file(error_path, job.tenant_id)

        job_tracker.complete_job(job_id, total_rows, success_rows, failed_rows, error_url)
    except ImportException as exc:
        logger.exception("Import job failed", extra={"job_id": job_id, "error": str(exc)})
        job_tracker.update_status(job_id, "failed", error_message=str(exc))
    except Exception as exc:
        logger.exception("Import job failed", extra={"job_id": job_id, "error": str(exc)})
        job_tracker.update_status(job_id, "failed", error_message="Unexpected import failure")
    finally:
        sem.release()
