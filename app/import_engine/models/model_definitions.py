from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class TransformationRule(BaseModel):
    type: str
    source: Optional[str] = None
    target: Optional[str] = None
    targets: Optional[List[str]] = None
    delimiter: Optional[str] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        allowed = {"uppercase", "lowercase", "split"}
        normalized = value.strip().lower()
        if normalized not in allowed:
            raise ValueError(f"Unsupported transformation type '{value}'")
        return normalized


class FieldDefinition(BaseModel):
    name: str
    type: str = "str"
    required: bool = False
    unique: bool = False
    regex: Optional[str] = None
    default: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field name is required")
        return value

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"str", "int", "float", "bool"}
        if normalized not in allowed:
            raise ValueError(f"Unsupported field type '{value}'")
        return normalized


class ModelDefinition(BaseModel):
    name: str
    table: str
    fields: List[FieldDefinition]
    transformations: List[TransformationRule] = Field(default_factory=list)
    lock_table: bool = False

    @field_validator("name", "table")
    @classmethod
    def validate_basic_identifiers(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Identifier is required")
        return value

    @model_validator(mode="after")
    def validate_uniqueness(self):
        names = [field.name for field in self.fields]
        if len(names) != len(set(names)):
            raise ValueError(f"Duplicate field names found in model '{self.name}'")
        return self

    def field_names(self) -> List[str]:
        return [f.name for f in self.fields]

    def unique_fields(self) -> List[str]:
        return [f.name for f in self.fields if f.unique]

    def regex_rules(self) -> dict:
        return {f.name: f.regex for f in self.fields if f.regex}

    def required_fields(self) -> List[str]:
        return [f.name for f in self.fields if f.required]

    def column_types(self) -> dict:
        return {f.name: f.type for f in self.fields}

    def alias_map(self) -> dict:
        return {f.name: f.aliases for f in self.fields if f.aliases}
