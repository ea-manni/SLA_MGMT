from __future__ import annotations

import json
from eap_client import get_eap_client
from schemas import VendorContractSpec, MetricEvaluationResult, MonthlyAuditReport


def generate_audit_report(
    spec: VendorContractSpec,
    billing_period: str,
    evaluations: list[MetricEvaluationResult],
) -> MonthlyAuditReport:
    """Calculates overall claims against contract caps and formats an executive notice using the EAP Agent."""
    total_claim = sum(e.breach_amount_usd for e in evaluations)
    breaches = sum(1 for e in evaluations if not e.passed)

    # Enforce contractual liability caps
    max_cap_usd = spec.monthly_fee_usd * (spec.remedy_cap_percent_of_fee / 100.0)
    final_claim = min(total_claim, max_cap_usd)

    eval_json = json.dumps([e.model_dump() for e in evaluations], indent=2)

    prompt = f"""You are the Senior Vendor Management Auditor for Equinix operations.
Review these deterministic SLA compliance audit results and draft an executive claim summary for procurement and vendor relations.

Vendor Name: {spec.vendor_name}
Contract ID: {spec.contract_id}
Billing Period: {billing_period}
Monthly Base Fee: ${spec.monthly_fee_usd:,.2f}
Total Breaches Detected: {breaches}
Raw Calculated Remedy: ${total_claim:,.2f}
Contract Capped Final Remedy: ${final_claim:,.2f}

Detailed Metric Breakdown:
{eval_json}

Draft a clear, professional 2-3 paragraph executive summary citing specific sections and stating the exact credit owed.
"""

    print("[*] Generating audit executive rationale via EAP Agent...")
    client = get_eap_client()
    executive_summary = client.invoke(prompt)

    return MonthlyAuditReport(
        vendor_id=spec.vendor_id,
        vendor_name=spec.vendor_name,
        billing_period=billing_period,
        total_metrics_evaluated=len(evaluations),
        breaches_detected=breaches,
        total_claim_usd=round(final_claim, 2),
        executive_summary=executive_summary.strip(),
        evaluations=evaluations,
    )