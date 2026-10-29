from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from schemas import VendorContractSpec
from ingest_sla import ingest_sla_contract
from ingest_performance import ingest_monthly_performance
from evaluate import evaluate_compliance
from reasoning import generate_audit_report


class SlaAuditorGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Vendor SLA Compliance & Penalty Auditor")
        self.root.geometry("980x740")
        self.root.minsize(800, 600)

        # State cache
        self.current_report = None
        self.specs_dir = Path("data/specs")
        self.specs_dir.mkdir(parents=True, exist_ok=True)
        Path("data/reports").mkdir(parents=True, exist_ok=True)

        self._build_ui()

    def _build_ui(self):
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: Onboarding
        self.tab_onboard = ttk.Frame(notebook)
        notebook.add(self.tab_onboard, text="1. Vendor Onboarding")
        self._build_onboard_tab()

        # Tab 2: Monthly Audit & Approval
        self.tab_audit = ttk.Frame(notebook)
        notebook.add(self.tab_audit, text="2. Monthly Audit & Manager Approval")
        self._build_audit_tab()

    # -------------------------------------------------------------
    # TAB 1: ONBOARDING
    # -------------------------------------------------------------
    def _build_onboard_tab(self):
        frame = ttk.LabelFrame(self.tab_onboard, text="Onboard Vendor Contract / SLA", padding=15)
        frame.pack(fill="x", padx=10, pady=10)

        lbl = ttk.Label(frame, text="Select Vendor SLA Document (.txt, .md, .pdf):")
        lbl.grid(row=0, column=0, sticky="w", pady=5)

        self.sla_file_var = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=self.sla_file_var, width=60)
        entry.grid(row=1, column=0, padx=(0, 10), sticky="ew")

        btn_browse = ttk.Button(frame, text="Browse...", command=self._browse_sla_file)
        btn_browse.grid(row=1, column=1, padx=5)

        btn_onboard = ttk.Button(frame, text="Ingest & Extract SLA Spec", command=self._run_onboarding)
        btn_onboard.grid(row=1, column=2, padx=5)

        # Output Text Box
        lbl_out = ttk.Label(self.tab_onboard, text="Extracted Vendor SLA Specification (JSON):")
        lbl_out.pack(anchor="w", padx=15, pady=(10, 0))

        self.txt_onboard_out = tk.Text(self.tab_onboard, height=25, wrap="none")
        self.txt_onboard_out.pack(fill="both", expand=True, padx=15, pady=5)

    def _browse_sla_file(self):
        f = filedialog.askopenfilename(
            title="Select Contract File",
            filetypes=[("Text & Document Files", "*.txt *.md *.pdf"), ("All Files", "*.*")]
        )
        if f:
            self.sla_file_var.set(f)

    def _run_onboarding(self):
        path = self.sla_file_var.get().strip()
        if not path or not Path(path).exists():
            messagebox.showerror("Error", "Please select a valid contract file.")
            return

        try:
            spec = ingest_sla_contract(path)
            out_json = json.dumps(spec.to_dict(), indent=2)
            self.txt_onboard_out.delete("1.0", tk.END)
            self.txt_onboard_out.insert(tk.END, out_json)
            messagebox.showinfo("Success", f"Vendor '{spec.vendor_name}' successfully onboarded!")
            self._refresh_vendor_dropdown()
        except Exception as e:
            messagebox.showerror("Ingestion Error", f"Failed to ingest SLA:\n{str(e)}")

    # -------------------------------------------------------------
    # TAB 2: AUDIT & DECISION APPROVAL
    # -------------------------------------------------------------
    def _build_audit_tab(self):
        # Controls Frame
        ctrl_frame = ttk.LabelFrame(self.tab_audit, text="Audit Execution Setup", padding=10)
        ctrl_frame.pack(fill="x", padx=10, pady=5)

        # Vendor Selector
        ttk.Label(ctrl_frame, text="Vendor:").grid(row=0, column=0, sticky="w", padx=5)
        self.cb_vendor = ttk.Combobox(ctrl_frame, state="readonly", width=30)
        self.cb_vendor.grid(row=0, column=1, padx=5, pady=5)

        # Billing Period
        ttk.Label(ctrl_frame, text="Billing Period:").grid(row=0, column=2, sticky="w", padx=5)
        self.period_var = tk.StringVar(value="July 2026")
        ttk.Entry(ctrl_frame, textvariable=self.period_var, width=15).grid(row=0, column=3, padx=5)

        # Performance Log File
        ttk.Label(ctrl_frame, text="Performance Log (.csv/.json):").grid(row=1, column=0, sticky="w", padx=5)
        self.perf_file_var = tk.StringVar()
        ttk.Entry(ctrl_frame, textvariable=self.perf_file_var, width=32).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(ctrl_frame, text="Browse...", command=self._browse_perf_file).grid(row=1, column=2, padx=5)

        btn_run_audit = ttk.Button(ctrl_frame, text="▶ Run Compliance Audit", command=self._run_audit)
        btn_run_audit.grid(row=1, column=3, padx=5, sticky="ew")

        self._refresh_vendor_dropdown()

        # Results TreeView (Table)
        table_frame = ttk.LabelFrame(self.tab_audit, text="Evaluation Results & Breach Penalties", padding=10)
        table_frame.pack(fill="both", expand=True, padx=10, pady=5)

        cols = ("metric", "status", "measured", "target", "remedy", "clause")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=6)
        self.tree.heading("metric", text="Metric Name")
        self.tree.heading("status", text="Status")
        self.tree.heading("measured", text="Measured")
        self.tree.heading("target", text="SLA Target")
        self.tree.heading("remedy", text="Claim Amount ($)")
        self.tree.heading("clause", text="Contract Clause")

        self.tree.column("metric", width=200)
        self.tree.column("status", width=80, anchor="center")
        self.tree.column("measured", width=90, anchor="center")
        self.tree.column("target", width=90, anchor="center")
        self.tree.column("remedy", width=120, anchor="e")
        self.tree.column("clause", width=250)
        self.tree.pack(fill="both", expand=True)

        # Executive Summary Box
        summary_frame = ttk.LabelFrame(self.tab_audit, text="AI Executive Summary / Procurement Rationale", padding=10)
        summary_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.txt_summary = tk.Text(summary_frame, height=5, wrap="word")
        self.txt_summary.pack(fill="both", expand=True)

        # Decision & Safeguard Bar
        decision_frame = ttk.Frame(self.tab_audit, padding=10)
        decision_frame.pack(fill="x", padx=10, pady=5)

        self.lbl_total_claim = ttk.Label(
            decision_frame, 
            text="Total Claim Due: $0.00", 
            font=("Segoe UI", 11, "bold")
        )
        self.lbl_total_claim.pack(side="left", padx=10)

        self.btn_reject = ttk.Button(
            decision_frame, 
            text="✕ Reject Claim", 
            command=lambda: self._record_decision("REJECTED"),
            state="disabled"
        )
        self.btn_reject.pack(side="right", padx=5)

        self.btn_approve = ttk.Button(
            decision_frame, 
            text="✓ Approve & Sign Off Claim", 
            command=lambda: self._record_decision("APPROVED"),
            state="disabled"
        )
        self.btn_approve.pack(side="right", padx=5)

    def _browse_perf_file(self):
        f = filedialog.askopenfilename(
            title="Select Monthly Incident Log",
            filetypes=[("Data Files", "*.csv *.json *.xlsx"), ("All Files", "*.*")]
        )
        if f:
            self.perf_file_var.set(f)

    def _refresh_vendor_dropdown(self):
        specs = list(self.specs_dir.glob("*_spec.json"))
        vendors = [p.stem.replace("_spec", "") for p in specs]
        self.cb_vendor["values"] = vendors
        if vendors and not self.cb_vendor.get():
            self.cb_vendor.current(0)

    def _run_audit(self):
        vendor_id = self.cb_vendor.get().strip()
        perf_file = self.perf_file_var.get().strip()
        period = self.period_var.get().strip()

        if not vendor_id:
            messagebox.showerror("Error", "Please select an onboarded vendor.")
            return
        if not perf_file or not Path(perf_file).exists():
            messagebox.showerror("Error", "Please select a valid performance data file.")
            return

        try:
            # 1. Load Spec
            spec_path = self.specs_dir / f"{vendor_id}_spec.json"
            with open(spec_path, "r", encoding="utf-8") as f:
                spec = VendorContractSpec.from_dict(json.load(f))

            # 2. Ingest Data & Evaluate
            perf_data = ingest_monthly_performance(perf_file)
            evaluations = evaluate_compliance(spec, perf_data)
            self.current_report = generate_audit_report(spec, period, evaluations)

            # 3. Update Table
            for item in self.tree.get_children():
                self.tree.delete(item)

            for ev in self.current_report.evaluations:
                status_str = "PASS" if ev.passed else "FAIL"
                self.tree.insert("", "end", values=(
                    ev.metric_name,
                    status_str,
                    f"{ev.measured_value} {ev.unit}",
                    f"{ev.target_threshold} {ev.unit}",
                    f"${ev.breach_amount_usd:,.2f}",
                    ev.cited_clause
                ))

            # 4. Update Summary & Total
            self.txt_summary.delete("1.0", tk.END)
            self.txt_summary.insert(tk.END, self.current_report.executive_summary)
            self.lbl_total_claim.config(text=f"Total Claim Due: ${self.current_report.total_claim_usd:,.2f}")

            # 5. Enable Decision Controls
            self.btn_approve.config(state="normal")
            self.btn_reject.config(state="normal")

        except Exception as e:
            messagebox.showerror("Audit Error", f"Failed to complete audit:\n{str(e)}")

    def _record_decision(self, decision: str):
        if not self.current_report:
            return

        confirm = messagebox.askyesno(
            "Confirm Action",
            f"Are you sure you want to mark this claim as {decision}?"
        )
        if not confirm:
            return

        audit_entry = {
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "decision": decision,
            "vendor_id": self.current_report.vendor_id,
            "vendor_name": self.current_report.vendor_name,
            "billing_period": self.current_report.billing_period,
            "total_claim_usd": self.current_report.total_claim_usd,
            "breaches_detected": self.current_report.breaches_detected,
            "report_data": self.current_report.to_dict()
        }

        # Append to audit trail log
        log_file = Path("data/audit_log.json")
        logs = []
        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            except Exception:
                logs = []

        logs.append(audit_entry)
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2)

        messagebox.showinfo(
            "Decision Saved", 
            f"Claim has been recorded as '{decision}'.\nAudit entry saved to data/audit_log.json"
        )

        # Disable buttons until next run
        self.btn_approve.config(state="disabled")
        self.btn_reject.config(state="disabled")


if __name__ == "__main__":
    root = tk.Tk()
    app = SlaAuditorGUI(root)
    root.mainloop()