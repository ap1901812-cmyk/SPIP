from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FileProcessingReport(BaseModel):
    filename: str
    dataset_type: str
    total_rows: int
    imported_records: int
    duplicate_records: int = 0
    error_records: int = 0


class ValidationErrorDetail(BaseModel):
    filename: str
    row: int
    field: str
    message: str


class AutoMasterDetail(BaseModel):
    entity_type: str
    code: str
    description_or_name: str


class MissingMasterDetail(BaseModel):
    entity_type: str
    code: str
    reason: str


class DataQualitySummary(BaseModel):
    success: bool = True
    files_processed: list[FileProcessingReport] = Field(default_factory=list)
    total_records_processed: int = 0
    duplicate_records_count: int = 0
    auto_generated_masters: list[AutoMasterDetail] = Field(default_factory=list)
    missing_masters: list[MissingMasterDetail] = Field(default_factory=list)
    validation_errors: list[ValidationErrorDetail] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DataQualityScanner:
    """Performs schema validation, duplicate detection, and builds structured Data Quality Summaries."""

    def __init__(self) -> None:
        self.summary = DataQualitySummary()

    def add_file_report(self, report: FileProcessingReport) -> None:
        self.summary.files_processed.append(report)
        self.summary.total_records_processed += report.total_rows
        self.summary.duplicate_records_count += report.duplicate_records

    def add_validation_error(self, filename: str, row: int, field: str, message: str) -> None:
        self.summary.validation_errors.append(
            ValidationErrorDetail(filename=filename, row=row, field=field, message=message)
        )

    def add_auto_generated_master(self, entity_type: str, code: str, desc: str) -> None:
        self.summary.auto_generated_masters.append(
            AutoMasterDetail(entity_type=entity_type, code=code, description_or_name=desc)
        )

    def add_missing_master(self, entity_type: str, code: str, reason: str) -> None:
        self.summary.missing_masters.append(
            MissingMasterDetail(entity_type=entity_type, code=code, reason=reason)
        )

    def add_warning(self, warning_message: str) -> None:
        if warning_message not in self.summary.warnings:
            self.summary.warnings.append(warning_message)

    def finalize() -> DataQualitySummary:
        if self.summary.validation_errors and not self.summary.files_processed:
            self.summary.success = False
        return self.summary
