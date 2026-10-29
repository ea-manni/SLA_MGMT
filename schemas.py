from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import List, Optional


@dataclass
class SlaMetricSpec:
    metric_id: str
    metric_name: str
    target_threshold: float
    unit: str
    comparator: str
    remedy_type: str
    clause_section: str
    clause_title: str
    clause_excerpt: str
    remedy_rate_percent: Optional[float] = None
    remedy_flat_usd: Optional[float] = None


@dataclass
class VendorContractSpec:
    vendor_id: str
    vendor_name: str
    contract_id: str
    monthly_fee_usd: float
    metrics: List[SlaMetricSpec]
    remedy_cap_percent_of_fee: float = 100.0

    @classmethod
    def from_dict(cls, d: dict) -> VendorContractSpec:
        metrics = [SlaMetricSpec(**m) for m in d.get("metrics", [])]
        return cls(
            vendor_id=d["vendor_id"],
            vendor_name=d["vendor_name"],
            contract_id=d["contract_id"],
            monthly_fee_usd=float(d["monthly_fee_usd"]),
            remedy_cap_percent_of_fee=float(d.get("remedy_cap_percent_of_fee", 100.0)),
            metrics=metrics,
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MetricEvaluationResult:
    metric_id: str
    metric_name: str
    measured_value: float
    target_threshold: float
    unit: str
    passed: bool
    breach_amount_usd: float
    cited_clause: str
    notes: Optional[str] = None


@dataclass
class MonthlyAuditReport:
    vendor_id: str
    vendor_name: str
    billing_period: str
    total_metrics_evaluated: int
    breaches_detected: int
    total_claim_usd: float
    executive_summary: str
    evaluations: List[MetricEvaluationResult]

    def to_dict(self) -> dict:
        return asdict(self)