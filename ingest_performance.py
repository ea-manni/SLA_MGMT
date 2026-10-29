from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict


def ingest_monthly_performance(file_path: str) -> Dict[str, float]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Performance file does not exist: {file_path}")

    print(f"[*] Parsing monthly performance file: {file_path}")

    # JSON input
    if path.suffix.lower() == ".json":
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
            return {str(k).lower().strip(): float(v) for k, v in raw.items()}

    # CSV input (using standard library csv)
    if path.suffix.lower() == ".csv":
        normalized_metrics: Dict[str, float] = {}
        with open(path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if not rows:
                raise ValueError(f"CSV file is empty: {file_path}")

            # Standardize header keys
            cleaned_rows = []
            for r in rows:
                cleaned_rows.append({k.strip().lower().replace(" ", "_"): v for k, v in r.items() if k})

            # Check if format is metric_id, value
            if "metric_id" in cleaned_rows[0] and "value" in cleaned_rows[0]:
                for r in cleaned_rows:
                    normalized_metrics[r["metric_id"].strip().lower()] = float(r["value"])
                return normalized_metrics

            # Raw incident calculations
            mttr_vals = [float(r["mttr_hours"]) for r in cleaned_rows if "mttr_hours" in r and r["mttr_hours"]]
            if mttr_vals:
                normalized_metrics["mttr"] = sum(mttr_vals) / len(mttr_vals)

            resp_vals = [float(r["response_time_minutes"]) for r in cleaned_rows if "response_time_minutes" in r and r["response_time_minutes"]]
            if resp_vals:
                normalized_metrics["response_time"] = max(resp_vals)

            uptime_vals = [float(r["uptime_percentage"]) for r in cleaned_rows if "uptime_percentage" in r and r["uptime_percentage"]]
            if uptime_vals:
                normalized_metrics["uptime_pct"] = min(uptime_vals)

            return normalized_metrics

    raise ValueError(f"Please provide CSV or JSON performance data: {file_path}")