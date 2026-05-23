from pathlib import Path

import pandas as pd

from app.db.session import get_job_db
from app.import_engine.models.model_definitions import ModelDefinition
from app.import_engine.profile_defaults import DEFAULT_IMPORT_PROFILES
from app.models.import_profile import ImportProfile
from app.utils.exceptions import ValidationException


def _model_dump(model):
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


class ImportProfileService:
    def seed_defaults(self):
        db = get_job_db()
        try:
            for profile in DEFAULT_IMPORT_PROFILES:
                existing = (
                    db.query(ImportProfile)
                    .filter(ImportProfile.tenant_id == profile["tenant_id"], ImportProfile.name == profile["name"])
                    .first()
                )
                if existing:
                    continue
                db.add(ImportProfile(**profile))
            db.commit()
        finally:
            db.close()

    def list_profiles(self, tenant_id: str):
        db = get_job_db()
        try:
            return (
                db.query(ImportProfile)
                .filter(ImportProfile.tenant_id == tenant_id)
                .order_by(ImportProfile.is_default.desc(), ImportProfile.name.asc())
                .all()
            )
        finally:
            db.close()

    def resolve_profile(self, tenant_id: str, file_path: str, original_filename: str | None = None):
        profiles = self.list_profiles(tenant_id)
        if not profiles:
            raise ValidationException(f"No import profiles configured for tenant '{tenant_id}'")

        file_insights = inspect_file_structure(file_path, original_filename=original_filename)
        scored_profiles = []
        for profile in profiles:
            score = self._score_profile(profile, file_insights)
            scored_profiles.append((score, profile))

        scored_profiles.sort(key=lambda item: (item[0], item[1].is_default), reverse=True)
        best_score, best_profile = scored_profiles[0]
        if best_score <= 0:
            raise ValidationException(f"No matching import profile found for tenant '{tenant_id}'")
        return best_profile

    def build_request_components(self, tenant_id: str, file_path: str, original_filename: str | None = None):
        profile = self.resolve_profile(tenant_id, file_path, original_filename=original_filename)
        model_definitions = [ModelDefinition(**model) for model in profile.model_definitions]
        return {
            "profile": profile,
            "model_definitions": model_definitions,
            "sheet_mapping": profile.sheet_mapping,
        }

    def _score_profile(self, profile: ImportProfile, file_insights: dict) -> int:
        score = 0
        filename = file_insights["filename"]
        all_headers = file_insights["all_headers"]
        sheet_names = set(file_insights["sheet_names"])
        meaningful_match = False

        for pattern in profile.filename_contains or []:
            if pattern.lower() in filename:
                score += 5
                meaningful_match = True

        required_headers = set(profile.required_headers or [])
        if required_headers:
            matched_headers = {header for header in required_headers if header in all_headers}
            score += len(matched_headers) * 3
            if matched_headers:
                meaningful_match = True
            if matched_headers == required_headers:
                score += 6

        for sheet_name in (profile.sheet_mapping or {}).keys():
            if sheet_name in sheet_names and sheet_name.lower() != "csv":
                score += 4
                meaningful_match = True

        if profile.is_default and meaningful_match:
            score += 1

        return score if meaningful_match else 0


def inspect_file_structure(file_path: str, original_filename: str | None = None) -> dict:
    path = Path(file_path)
    extension = path.suffix.lower()
    all_headers = set()
    sheet_names = []

    if extension == ".csv":
        frame = pd.read_csv(path, nrows=0)
        headers = [str(column) for column in frame.columns]
        all_headers.update(headers)
        sheet_names = ["csv"]
    else:
        workbook = pd.ExcelFile(path)
        sheet_names = list(workbook.sheet_names)
        for sheet in sheet_names:
            frame = pd.read_excel(workbook, sheet_name=sheet, nrows=0)
            all_headers.update(str(column) for column in frame.columns)

    return {
        "filename": (original_filename or path.name).lower(),
        "sheet_names": sheet_names,
        "all_headers": all_headers,
    }
