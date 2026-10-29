from __future__ import annotations

import argparse
from pathlib import Path
from ingest_sla import ingest_sla_contract
from ingest_performance import ingest_monthly_performance
from evaluate import evaluate_compliance
from reasoning import generate_audit_report
from schemas import VendorContractSpec


def load_spec(vendor_id: str) -> VendorContractSpec:
    spec_path = Path("data/specs") / f"{vendor_id}_spec.json"
    if not spec_path.exists():
        raise FileNotFoundError(
            f"Vendor specification not found at {spec_path}. "
            f"Please onboard the vendor first using: python main.py --onboard-sla <file>"
        )
    with open(spec_path, "r", encoding="utf-8") as f:
        return VendorContractSpec.model_validate_json(f.read())


def main():
    parser = argparse.ArgumentParser(description="Vendor SLA Compliance & Penalty Auditor")
    parser.add_argument("--onboard-sla", help="Path to vendor contract file (PDF or TXT) to onboard")
    parser.add_argument("--vendor", help="Vendor identifier slug (e.g., vertiv, schneider)")
    parser.add_argument("--performance-log", help="Path to monthly incident/performance log (CSV, XLSX, or JSON)")
    parser.add_argument("--period", default="Current Billing Period", help="Billing period label (e.g., 'July 2026')")

    args = parser.parse_args()

    # Flow 1: Onboard Vendor SLA Contract
    if args.onboard_sla:
        spec = ingest_sla_contract(args.onboard_sla)
        print("\n" + "=" * 60)
        print(f"ONBOARDING COMPLETE: {spec.vendor_name} (ID: {spec.vendor_id})")
        print("=" * 60)
        print(f"Contract Reference : {spec.contract_id}")
        print(f"Monthly Base Fee   : ${spec.monthly_fee_usd:,.2f}")
        print(f"Total Metrics Bound: {len(spec.metrics)}")
        for m in spec.metrics:
            print(f"  - [{m.metric_id}] {m.metric_name}: {m.comparator} {m.target_threshold} {m.unit} -> Clause {m.clause_section}")
        return

    # Flow 2: Monthly Audit
    if args.vendor and args.performance_log:
        spec = load_spec(args.vendor)
        perf_data = ingest_monthly_performance(args.performance_log)
        evaluations = evaluate_compliance(spec, perf_data)
        report = generate_audit_report(spec, args.period, evaluations)

        # Save report JSON
        out_dir = Path("data/reports")
        out_dir.mkdir(parents=True, exist_ok=True)
        safe_period = args.period.replace(" ", "_").replace("/", "-")
        report_file = out_dir / f"{args.vendor}_{safe_period}_audit.json"

        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))

        print("\n" + "=" * 60)
        print(f"SLA AUDIT REPORT: {report.vendor_name} — {report.billing_period}")
        print("=" * 60)
        print(f"Total Metrics Checked : {report.total_metrics_evaluated}")
        print(f"Breaches Identified    : {report.breaches_detected}")
        print(f"Total Remedy Due       : ${report.total_claim_usd:,.2f}")
        print("-" * 60)
        print("Detailed Metric Results:")
        for ev in report.evaluations:
            status = "PASS" if ev.passed else "FAIL"
            print(f"  [{status}] {ev.metric_name}: Actual {ev.measured_value} {ev.unit} vs Target {ev.target_threshold} {ev.unit}")
            if not ev.passed:
                print(f"         Remedy: ${ev.breach_amount_usd:,.2f} | Clause: {ev.cited_clause}")
                if ev.notes:
                    print(f"         Notes: {ev.notes}")

        print("\nExecutive Summary for Procurement:")
        print(report.executive_summary)
        print(f"\n[+] Full structured audit record saved to: {report_file}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()