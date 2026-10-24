"""
MNP Centralized Cloud-Based Payroll Subsystem (BTM 495 Working Prototype)
Unified REST API Server with built-in HTTP engine and zero third-party dependency lock.
Exposes JSON endpoints for Claude Design frontend and automated testing.
"""

import json
import os
import sys
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Timer

# Add project root to Python module path
sys.path.insert(0, str(Path(__file__).parent))

from database.db import db
from services.employee_service import EmployeeService
from services.timesheet_service import TimesheetService
from services.compensation_service import CompensationService
from services.remittance_service import RemittanceService
from services.payroll_service import PayrollService

class PayrollAPIHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests with full CORS and JSON support."""

    def _set_headers(self, status=200, content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_OPTIONS(self):
        """Pre-flight CORS handler."""
        self._set_headers(204)

    def do_HEAD(self):
        """Handles HEAD requests identically to GET."""
        self.do_GET()

    def _parse_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            body = self.rfile.read(content_length)
            return json.loads(body.decode("utf-8"))
        return {}

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        try:
            # 0. Serve Frontend UI Dashboard
            if path in ("/", "/index.html"):
                html_path = Path(__file__).parent / "frontend" / "index.html"
                if html_path.exists():
                    with open(html_path, "rb") as f:
                        content = f.read()
                    self._set_headers(200, content_type="text/html; charset=utf-8")
                    self.wfile.write(content)
                    return
                else:
                    self._set_headers(404, content_type="text/plain")
                    self.wfile.write(b"Frontend not found")
                    return
            # 1. Healthcheck
            if path == "/api/health":
                self._set_headers(200)
                self.wfile.write(json.dumps({"status": "healthy", "service": "MNP Payroll Subsystem"}).encode("utf-8"))

            # 2. Multi-Tenant Clients
            elif path == "/api/clients":
                clients = db.query_all("SELECT * FROM clients ORDER BY client_id ASC")
                self._set_headers(200)
                self.wfile.write(json.dumps({"clients": clients}).encode("utf-8"))

            # 3. UC1: Employees by Client
            elif path == "/api/employees":
                client_id = int(query.get("client_id", [101])[0])
                employees = EmployeeService.get_employees_by_client(client_id)
                self._set_headers(200)
                self.wfile.write(json.dumps({"client_id": client_id, "employees": employees}).encode("utf-8"))

            # 4. UC2: Timesheets by Client
            elif path == "/api/timesheets":
                client_id = int(query.get("client_id", [101])[0])
                timesheets = TimesheetService.get_timesheets_for_client(client_id)
                self._set_headers(200)
                self.wfile.write(json.dumps({"client_id": client_id, "timesheets": timesheets}).encode("utf-8"))

            # 5. UC3: SOX Audit Trail Badges
            elif path == "/api/compensation/audit":
                client_id = int(query.get("client_id", [101])[0])
                audit_records = CompensationService.get_audit_trail(client_id=client_id)
                self._set_headers(200)
                self.wfile.write(json.dumps({"audit_trail": audit_records}).encode("utf-8"))

            # 6. UC4: Statutory Remittances
            elif path == "/api/remittances":
                run_id = int(query.get("run_id", [1])[0])
                remittance = RemittanceService.get_remittance_by_run(run_id)
                self._set_headers(200)
                self.wfile.write(json.dumps({"remittance": remittance}).encode("utf-8"))

            # 7. UC5: Payroll Runs
            elif path == "/api/payroll/runs":
                client_id = int(query.get("client_id", [101])[0])
                runs = PayrollService.get_runs_by_client(client_id)
                self._set_headers(200)
                self.wfile.write(json.dumps({"client_id": client_id, "payroll_runs": runs}).encode("utf-8"))

            # 8. UC5: Pay Stubs for a Run
            elif path == "/api/payroll/stubs":
                run_id = int(query.get("run_id", [1])[0])
                stubs = PayrollService.get_stubs_by_run(run_id)
                self._set_headers(200)
                self.wfile.write(json.dumps({"run_id": run_id, "pay_stubs": stubs}).encode("utf-8"))

            # 9. UC5: Tax Slips (T4 & Releve 1)
            elif path == "/api/payroll/tax-slips":
                client_id = int(query["client_id"][0]) if "client_id" in query else None
                employee_id = int(query["employee_id"][0]) if "employee_id" in query else None
                tax_year = int(query["tax_year"][0]) if "tax_year" in query else None
                slips = PayrollService.get_tax_slips(client_id=client_id, employee_id=employee_id, tax_year=tax_year)
                self._set_headers(200)
                self.wfile.write(json.dumps({"tax_slips": slips}).encode("utf-8"))

            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": f"Endpoint '{path}' not found."}).encode("utf-8"))

        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        body = self._parse_body()

        try:
            # 1. UC1: Onboard Employee
            if path == "/api/employees":
                res = EmployeeService.create_employee(
                    client_id=int(body.get("client_id", 101)),
                    first_name=body["first_name"],
                    last_name=body["last_name"],
                    email=body["email"],
                    phone=body.get("phone", "514-555-0100"),
                    hire_date=body.get("hire_date", "2026-10-01"),
                    institution_number=body.get("institution_number", "001"),
                    transit_number=body.get("transit_number", "10234"),
                    account_number=body.get("account_number", "1234567"),
                    account_type=body.get("account_type", "Checking"),
                    job_title=body.get("job_title", "Staff Associate"),
                    department=body.get("department", "Operations"),
                    employment_type=body.get("employment_type", "Full-Time"),
                    hourly_rate=float(body.get("hourly_rate", 25.0)),
                    base_salary=float(body.get("base_salary", 0.0))
                )
                self._set_headers(201)
                self.wfile.write(json.dumps(res).encode("utf-8"))

            # 1b. UC1: Edit Employee Record (SubFlow 3S.2)
            elif path == "/api/employees/update":
                emp_id = int(body["employee_id"])
                res = EmployeeService.update_employee(
                    employee_id=emp_id,
                    first_name=body.get("first_name"),
                    last_name=body.get("last_name"),
                    email=body.get("email"),
                    phone=body.get("phone"),
                    status=body.get("status"),
                    institution_number=body.get("institution_number"),
                    transit_number=body.get("transit_number"),
                    account_number=body.get("account_number"),
                    account_type=body.get("account_type"),
                    job_title=body.get("job_title"),
                    department=body.get("department"),
                    employment_type=body.get("employment_type")
                )
                self._set_headers(200)
                self.wfile.write(json.dumps(res).encode("utf-8"))

            # 2. UC2: Submit Timesheet
            elif path == "/api/timesheets/submit":
                ts_id = int(body["timesheet_id"])
                res = TimesheetService.submit_timesheet(ts_id)
                self._set_headers(200)
                self.wfile.write(json.dumps(res).encode("utf-8"))

            # 3. UC2: Update Hours (with Lockout Check)
            elif path == "/api/timesheets/update":
                ts_id = int(body["timesheet_id"])
                reg = float(body["regular_hours"])
                ot = float(body["overtime_hours"])
                res = TimesheetService.update_hours(ts_id, reg, ot)
                self._set_headers(200)
                self.wfile.write(json.dumps(res).encode("utf-8"))

            # 4. UC3: Modify Wage & Create SOX Audit Log
            elif path == "/api/compensation/update":
                emp_id = int(body["employee_id"])
                new_rate = float(body["new_rate"])
                reason = body.get("reason", "Annual Performance Review")
                authorized_by = body.get("authorized_by", "Accounting Technician")
                res = CompensationService.update_employee_wage(emp_id, new_rate, reason, authorized_by)
                self._set_headers(200)
                self.wfile.write(json.dumps(res).encode("utf-8"))

            # 5. UC4: Transmit Statutory Remittance
            elif path == "/api/remittances/transmit":
                rem_id = int(body["remittance_id"])
                timeout = bool(body.get("simulate_timeout", False))
                res = RemittanceService.transmit_remittance(rem_id, simulate_timeout=timeout)
                self._set_headers(200)
                self.wfile.write(json.dumps(res).encode("utf-8"))

            # 6. UC5: Calculate New Pay Run
            elif path == "/api/payroll/calculate":
                client_id = int(body.get("client_id", 101))
                p_start = body.get("period_start", "2026-10-01")
                p_end = body.get("period_end", "2026-10-15")
                res = PayrollService.calculate_new_run(client_id, p_start, p_end)
                self._set_headers(201)
                self.wfile.write(json.dumps(res).encode("utf-8"))

            # 7. UC5: Approve Pay Run (Locks Timesheets)
            elif path == "/api/payroll/approve":
                run_id = int(body["run_id"])
                res = PayrollService.process_approval(run_id, approve=True)
                self._set_headers(200)
                self.wfile.write(json.dumps(res).encode("utf-8"))

            # 8. UC5: Reject Pay Run (Triggers Technician Alert Banner)
            elif path == "/api/payroll/reject":
                run_id = int(body["run_id"])
                reason = body.get("reason", "Discrepancy in reported hours")
                res = PayrollService.process_approval(run_id, approve=False, reason=reason)
                self._set_headers(200)
                self.wfile.write(json.dumps(res).encode("utf-8"))

            # 9. UC5: Generate Tax Slips (T4 & Releve 1)
            elif path == "/api/payroll/tax-slips/generate":
                client_id = int(body.get("client_id", 101))
                tax_year = int(body.get("tax_year", 2026))
                res = PayrollService.generate_tax_slips(client_id=client_id, tax_year=tax_year)
                self._set_headers(201)
                self.wfile.write(json.dumps(res).encode("utf-8"))

            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": f"POST endpoint '{path}' not found."}).encode("utf-8"))

        except PermissionError as pe:
            self._set_headers(403)
            self.wfile.write(json.dumps({"error": "Forbidden", "message": str(pe)}).encode("utf-8"))
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({"error": "Internal Error", "message": str(e)}).encode("utf-8"))


def run_server(port=None):
    if port is None:
        port = int(os.getenv("PORT", 8000))
    server_address = ("", port)
    httpd = HTTPServer(server_address, PayrollAPIHandler)
    print(f"============================================================")
    print(f" MNP Payroll Subsystem Prototype REST API Server")
    print(f" Web Dashboard: http://localhost:{port}")
    print(f" API Health:    http://localhost:{port}/api/health")
    print(f" Dual-mode: SQLite (payroll.db) + Supabase Cloud Engine")
    print(f"============================================================")

    # Automatically launch web browser on Windows/Mac/Linux
    if os.getenv("NO_BROWSER", "0") != "1":
        def open_browser():
            try:
                webbrowser.open(f"http://localhost:{port}")
            except Exception:
                pass
        Timer(1.2, open_browser).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Server Info] Shutting down gracefully.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
