from __future__ import annotations

import operator
from typing import List, Dict
from schemas import VendorContractSpec, MetricEvaluationResult

COMPARATORS = {
    "<=": operator.le,
    ">=": operator.ge,
    "<": operator.lt,
    ">": operator.gt,
    "==": operator.eq,
}


def evaluate_compliance(
    spec: VendorContractSpec,
    performance_metrics: Dict[str, float],
) -> List[MetricEvaluationResult]:
    """Deterministically checks performance against vendor contract thresholds without LLM hallucinations."""
    results: List[MetricEvaluationResult] = []

    for metric in spec.metrics:
        measured_val = performance_metrics.get(metric.metric_id)

        if measured_val is None:
            results.append(
                MetricEvaluationResult(
                    metric_id=metric.metric_id,
                    metric_name=metric.metric_name,
                    measured_value=0.0,
                    target_threshold=metric.target_threshold,
                    unit=metric.unit,
                    passed=False,
                    breach_amount_usd=0.0,
                    cited_clause=metric.clause_section,
                    notes="MISSING_DATA: Metric was omitted from monthly performance records.",
                )
            )
            continue

        comp_fn = COMPARATORS.get(metric.comparator, operator.le)
        passed = bool(comp_fn(measured_val, metric.target_threshold))

        remedy_amount = 0.0
        notes = None

        if not passed:
            if metric.remedy_flat_usd is not None and metric.remedy_flat_usd > 0:
                remedy_amount = metric.remedy_flat_usd
            elif metric.remedy_rate_percent is not None and metric.remedy_rate_percent > 0:
                remedy_amount = spec.monthly_fee_usd * (metric.remedy_rate_percent / 100.0)

            notes = (
                f"Breach detected: Actual {measured_val} {metric.unit} failed required "
                f"SLA target of {metric.comparator} {metric.target_threshold} {metric.unit}."
            )

        results.append(
            MetricEvaluationResult(
                metric_id=metric.metric_id,
                metric_name=metric.metric_name,
                measured_value=round(measured_val, 2),
                target_threshold=metric.target_threshold,
                unit=metric.unit,
                passed=passed,
                breach_amount_usd=round(remedy_amount, 2),
                cited_clause=f"{metric.clause_section}: {metric.clause_title}",
                notes=notes,
            )
        )

    return results