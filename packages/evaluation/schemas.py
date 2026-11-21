"""Versioned annotation and prediction contracts, exportable as JSON Schema."""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Status = Literal["VERIFIED", "CONTRADICTED", "UNVERIFIED", "ABSTAIN", "PARTIALLY_VERIFIED", "NOT_FOUND", "SKIPPED"]
Split = Literal["DEVELOPMENT", "VALIDATION", "TEST"]
Origin = Literal["SYNTHETIC", "ATTORNEY_LABELED"]


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, str_strip_whitespace=True)


class LabelSource(Record):
    document_id: str = Field(min_length=1)
    source_run_id: str = Field(min_length=1)
    page: int = Field(ge=1)
    block_id: str = Field(min_length=1)
    start: int = Field(ge=0)
    end: int = Field(ge=0)
    excerpt: str = Field(min_length=1)

    @model_validator(mode="after")
    def valid_span(self):
        if self.end <= self.start:
            raise ValueError("Label source offsets must be a nonempty half-open span")
        return self


class Annotation(Record):
    reviewer_ids: list[str] = Field(min_length=1)
    qualifications_confirmed: bool = False
    adjudicated: bool
    rationale: str = Field(min_length=1)
    sources: list[LabelSource] = Field(default_factory=list)


class LabelRecord(Record):
    schema_version: Literal[1] = 1
    item_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    case_family_id: str = Field(min_length=1)
    split: Split
    origin: Origin
    input_text: str = Field(min_length=1)
    source_hashes: list[str] = Field(default_factory=list)
    gold_status: Status
    error_types: list[str] = Field(default_factory=list)
    annotation: Annotation

    @field_validator("error_types", "source_hashes")
    @classmethod
    def unique_nonempty_values(cls, values):
        if any(not value.strip() for value in values) or len(set(values)) != len(values):
            raise ValueError("Labels/hashes must be nonempty and unique")
        return sorted(values)

    @model_validator(mode="after")
    def review_provenance(self):
        reviewers = self.annotation.reviewer_ids
        if any(not reviewer.strip() for reviewer in reviewers) or len(set(reviewers)) != len(reviewers):
            raise ValueError("Reviewers must have distinct, nonempty identifiers")
        if self.origin == "ATTORNEY_LABELED" and (
            len(reviewers) < 2 or not self.annotation.qualifications_confirmed or not self.annotation.adjudicated
        ):
            raise ValueError("Attorney labels require two qualified reviewers and adjudication")
        if self.gold_status == "VERIFIED" and (self.error_types or not self.annotation.sources):
            raise ValueError("VERIFIED gold labels require source spans and no labeled errors")
        return self


class PredictionRecord(Record):
    schema_version: Literal[1] = 1
    item_id: str = Field(min_length=1)
    run_id: str = Field(min_length=1)
    system_version: str = Field(min_length=1)
    status: Status
    error_types: list[str] = Field(default_factory=list)
    latency_ms: float | None = Field(default=None, ge=0)
    cost: float | None = Field(default=None, ge=0)
    cost_currency: str | None = Field(default=None, min_length=1)
    review_seconds: float | None = Field(default=None, ge=0)

    @field_validator("error_types")
    @classmethod
    def unique_errors(cls, values):
        if any(not value.strip() for value in values) or len(set(values)) != len(values):
            raise ValueError("Predicted error types must be nonempty and unique")
        return sorted(values)

    @model_validator(mode="after")
    def cost_unit(self):
        if (self.cost is None) != (self.cost_currency is None):
            raise ValueError("Cost and its currency must be supplied together")
        return self


AdjudicationVerdict = Literal[
    "TRUE_DEFECT_UNLISTED",
    "TRUE_DEFECT_TOKEN_MISMATCH",
    "DUPLICATE_FINDING",
    "OVERREACH_FALSE_POSITIVE",
    "ADVISORY_MISCLASSIFIED",
]

OfflineReachability = Literal[
    "OFFLINE_VERIFIABLE",
    "EXTERNAL_SOURCE_REQUIRED",
    "SOURCE_AVAILABLE_MISSED",
]


class UnadjudicatedAlertCandidate(Record):
    schema_version: Literal[1] = 1
    alert_id: str = Field(min_length=1)
    document_key: str = Field(min_length=1)
    finding_id: str = Field(default="")
    finding_type: str = Field(min_length=1)
    status: str = Field(min_length=1)
    severity: str = Field(min_length=1)
    evidence_grade: str = Field(min_length=1)
    engine: str = Field(default="")
    page: int | None = Field(default=None, ge=1)
    block_id: str | None = Field(default=None)
    span: tuple[int, int] | None = Field(default=None)
    title: str = Field(min_length=1)
    excerpt: str = Field(default="")
    cluster_id: str = Field(min_length=1)
    is_duplicate_in_cluster: bool = False


class AlertAdjudicationRecord(Record):
    schema_version: Literal[1] = 1
    alert_id: str = Field(min_length=1)
    document_key: str = Field(min_length=1)
    finding_type: str = Field(min_length=1)
    verdict: AdjudicationVerdict
    cluster_id: str = Field(min_length=1)
    reviewer_ids: list[str] = Field(min_length=1)
    adjudicated: bool = True
    rationale: str = Field(min_length=1)
    target_engine: str = Field(default="")

    @field_validator("reviewer_ids")
    @classmethod
    def valid_reviewers(cls, values: list[str]) -> list[str]:
        if any(not v.strip() for v in values) or len(set(values)) != len(values):
            raise ValueError("Reviewer identifiers must be distinct and nonempty")
        return values


class ReachabilityItemRecord(Record):
    schema_version: Literal[1] = 1
    item_key: str = Field(min_length=1)
    document_key: str = Field(min_length=1)
    defect_type: str = Field(min_length=1)
    hit: bool
    reachability: OfflineReachability
    reason: str = Field(min_length=1)

