from __future__ import annotations

import json
import os
import re
from pathlib import Path
from eap_client import get_eap_client
from schemas import VendorContractSpec


def extract_text_from_file(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Contract file does not exist: {file_path}")
    return path.read_text(encoding="utf-8", errors="replace")


def robust_json_decode(raw_text: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip(), flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
    match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if match:
        return json.loads(match.group(1))
    return json.loads(cleaned)


def ingest_sla_contract(file_path: str, output_dir: str = "data/specs") -> VendorContractSpec:
    raw_contract_text = extract_text_from_file(file_path)

    prompt = f"""You are the SLA Contract Extraction engine.
Extract all measurable SLA targets, thresholds, units, and contractual remedy clauses from this agreement into pure JSON.

JSON schema:
{{
  "vendor_id": "lowercase_slug_no_spaces",
  "vendor_name": "Full Vendor Name",
  "contract_id": "Contract Number",
  "monthly_fee_usd": 100000.0,
  "remedy_cap_percent_of_fee": 100.0,
  "metrics": [
    {{
      "metric_id": "mttr",
      "metric_name": "Mean Time to Resolve",
      "target_threshold": 4.0,
      "unit": "hours",
      "comparator": "<=",
      "remedy_type": "CREDIT",
      "remedy_rate_percent": 5.0,
      "remedy_flat_usd": null,
      "clause_section": "Section 4.1",
      "clause_title": "Emergency Restoration",
      "clause_excerpt": "Restoration exceeding 4 hours triggers a 5% credit."
    }}
  ]
}}

Contract Text:
{raw_contract_text}

Return ONLY the raw JSON object.
"""

    print(f"[*] Ingesting contract: {file_path} via EAP Agent...")
    client = get_eap_client()
    raw_response = client.invoke(prompt)

    parsed_dict = robust_json_decode(raw_response)
    spec = VendorContractSpec.from_dict(parsed_dict)

    os.makedirs(output_dir, exist_ok=True)
    out_file = Path(output_dir) / f"{spec.vendor_id}_spec.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(spec.to_dict(), f, indent=2)

    print(f"[+] Successfully extracted and saved structured spec: {out_file}")
    return spec