import random
import time
import csv
import os
from datetime import datetime
from dashboard import show_dashboard

# ----------------------------
# CONFIG
# ----------------------------
COUNTER_FILE = "wo_counter.txt"
WORK_ORDERS_CSV = "work_orders.csv"
FAULT_LOG_TXT = "fault_log.txt"
REPORT_TXT = "report_summary.txt"
FAULT_HISTORY_CSV = "fault_history.csv"

# Fault list with severity levels
FAULTS = [
    {"name": "Motor Overload", "severities": ["Minor", "Major", "Critical"]},
    {"name": "Sensor Failure", "severities": ["Minor", "Major", "Critical"]},
    {"name": "E-stop Triggered", "severities": ["Critical"]},
    {"name": "Power Outage", "severities": ["Major", "Critical"]},
    {"name": "Communication Error", "severities": ["Minor", "Major"]},
    {"name": "Motor Stalling", "severities": ["Major", "Critical"]},
    {"name": "Sensor Calibration Error", "severities": ["Major"]},
    {"name": "Power Surge", "severities": ["Critical"]},
]

# Stats
fault_count = {f["name"]: 0 for f in FAULTS}
total_repair_time = 0
total_downtime_seconds = 0
last_event = None

# Technician score
score = {"correct": 0, "incorrect": 0, "accuracy": 0, "grade": "-"}

# Escalation / site status tracking
status_flags = {
    "escalations": 0,
    "critical_wrong": 0,
    "sla_breaches": 0,
    "high_sla_breaches": 0,
    "site_status": "NORMAL",  # NORMAL | WATCH | STOP WORK
}

# In-memory event history for CSV export
event_history = []

# ----------------------------
# TIME HELPERS
# ----------------------------
def now_iso() -> str:
    return datetime.now().isoformat(sep=" ", timespec="seconds")


def _parse_dt(value: str):
    """
    Parses timestamps from:
    - ISO: "2026-02-09 00:13:12" or with "T"
    - time.ctime: "Sun Feb  9 00:13:12 2026"
    Returns datetime or None.
    """
    if not value:
        return None
    v = value.strip()
    v2 = v.replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(v2, fmt)
        except:
            pass
    try:
        return datetime.strptime(v, "%a %b %d %H:%M:%S %Y")
    except:
        pass
    try:
        return datetime.strptime(v, "%a %b  %d %H:%M:%S %Y")
    except:
        pass
    return None


def _age_minutes(created_ts: str) -> int:
    dt = _parse_dt(created_ts)
    if not dt:
        return -1
    delta = datetime.now() - dt
    mins = int(delta.total_seconds() // 60)
    return max(mins, 0)


# ----------------------------
# UTILS: PRIORITY + SLA
# ----------------------------
def severity_to_priority(sev: str) -> str:
    sev = (sev or "").strip().lower()
    if sev == "critical":
        return "HIGH"
    if sev == "major":
        return "MEDIUM"
    return "LOW"


def priority_to_sla_minutes(priority: str) -> int:
    p = (priority or "").strip().upper()
    if p == "HIGH":
        return 15
    if p == "MEDIUM":
        return 60
    return 240


def priority_rank(priority: str) -> int:
    p = (priority or "").strip().upper()
    return 0 if p == "HIGH" else 1 if p == "MEDIUM" else 2


# ----------------------------
# WORK ORDER ID (PERSISTENT)
# ----------------------------
def _ensure_counter_file():
    if not os.path.exists(COUNTER_FILE):
        with open(COUNTER_FILE, "w", encoding="utf-8") as f:
            f.write("0")


def next_work_order_id() -> str:
    _ensure_counter_file()
    try:
        with open(COUNTER_FILE, "r", encoding="utf-8") as f:
            current = int(f.read().strip() or "0")
    except:
        current = 0

    current += 1
    with open(COUNTER_FILE, "w", encoding="utf-8") as f:
        f.write(str(current))

    return f"WO-{current:06d}"


# ----------------------------
# WORK ORDER CSV (SCHEMA + UPDATE)
# ----------------------------
WORK_ORDER_COLUMNS = [
    "WO_ID",
    "Created_Timestamp",
    "Fault",
    "Severity",
    "Priority",
    "Status",                # OPEN / IN_PROGRESS / BREACHED / CLOSED
    "SLA_Minutes",
    "Result",
    "Escalation",
    "Site_Status",
    "Technician_Action",
    "Repair_Time_Min",
    "Work_Order_File",
    "Last_Updated",
    "Closed_Timestamp",
    "Closeout_Notes",
    "Breach_Reason",         # NEW: why it breached (e.g., SLA exceeded)
]


def ensure_work_orders_csv_schema():
    if not os.path.exists(WORK_ORDERS_CSV):
        with open(WORK_ORDERS_CSV, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(WORK_ORDER_COLUMNS)
        return

    with open(WORK_ORDERS_CSV, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    if not rows:
        with open(WORK_ORDERS_CSV, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(WORK_ORDER_COLUMNS)
        return

    existing_header = rows[0]
    if existing_header == WORK_ORDER_COLUMNS:
        return

    old_cols = existing_header
    data_rows = rows[1:]

    upgraded = []
    for r in data_rows:
        d = {old_cols[i]: (r[i] if i < len(r) else "") for i in range(len(old_cols))}
        for col in WORK_ORDER_COLUMNS:
            if col not in d:
                d[col] = ""
        upgraded.append(d)

    with open(WORK_ORDERS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(WORK_ORDER_COLUMNS)
        for d in upgraded:
            w.writerow([d.get(col, "") for col in WORK_ORDER_COLUMNS])


def append_work_order_to_queue(wo_row: dict):
    ensure_work_orders_csv_schema()
    with open(WORK_ORDERS_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([wo_row.get(col, "") for col in WORK_ORDER_COLUMNS])


def update_work_order_row(wo_id: str, updates: dict) -> bool:
    ensure_work_orders_csv_schema()

    with open(WORK_ORDERS_CSV, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    header = rows[0]
    idx_map = {name: i for i, name in enumerate(header)}
    updated = False

    for i in range(1, len(rows)):
        if len(rows[i]) < len(header):
            rows[i] += [""] * (len(header) - len(rows[i]))
        if rows[i][idx_map["WO_ID"]] == wo_id:
            for k, v in updates.items():
                if k in idx_map:
                    rows[i][idx_map[k]] = str(v)
            updated = True
            break

    if updated:
        with open(WORK_ORDERS_CSV, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)

    return updated


# ----------------------------
# SLA BREACH ESCALATION
# ----------------------------
def _safe_int(v, default=999999):
    try:
        return int(str(v).strip())
    except:
        return default


def sla_breach_escalation_scan():
    """
    Scans work_orders.csv:
    - If OPEN/IN_PROGRESS and AGE > SLA => mark BREACHED, escalate, update site status
    - Updates global status_flags counts and site status
    """
    ensure_work_orders_csv_schema()
    if not os.path.exists(WORK_ORDERS_CSV):
        return

    # Reset breach counters each scan
    status_flags["sla_breaches"] = 0
    status_flags["high_sla_breaches"] = 0

    with open(WORK_ORDERS_CSV, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for r in rows:
        st = (r.get("Status", "") or "").strip().upper()
        if st not in ("OPEN", "IN_PROGRESS"):
            continue

        created = r.get("Created_Timestamp", "")
        age = _age_minutes(created)
        sla = _safe_int(r.get("SLA_Minutes"), 999999)

        if age >= 0 and sla != 999999 and age > sla:
            status_flags["sla_breaches"] += 1
            if (r.get("Priority", "") or "").strip().upper() == "HIGH":
                status_flags["high_sla_breaches"] += 1

            wo_id = r.get("WO_ID", "")
            # Update row to BREACHED (idempotent)
            update_work_order_row(wo_id, {
                "Status": "BREACHED",
                "Escalation": "AUTO ESCALATE: SLA BREACH",
                "Site_Status": "WATCH",  # may be overridden below
                "Breach_Reason": f"SLA exceeded (AGE {age}m > SLA {sla}m)",
                "Last_Updated": now_iso(),
            })

    # Site status rules based on breaches (plus existing safety rules)
    # If 2+ HIGH breaches => STOP WORK
    if status_flags["high_sla_breaches"] >= 2:
        status_flags["site_status"] = "STOP WORK"
    elif status_flags["sla_breaches"] >= 1:
        # any breach => WATCH unless already STOP WORK
        if status_flags["site_status"] != "STOP WORK":
            status_flags["site_status"] = "WATCH"
    else:
        # keep NORMAL unless safety rules already made it stricter
        if status_flags["critical_wrong"] >= 2:
            status_flags["site_status"] = "STOP WORK"
        elif status_flags["escalations"] >= 3:
            status_flags["site_status"] = "WATCH"
        else:
            status_flags["site_status"] = "NORMAL"


# ----------------------------
# SUPERVISOR QUEUE VIEW
# ----------------------------
def supervisor_queue_view(limit: int = 15):
    """
    Shows OPEN + IN_PROGRESS + BREACHED (active), sorted:
    - Breached first
    - Priority (HIGH -> LOW)
    - SLA minutes (shortest first)
    - Age (oldest first)
    """
    sla_breach_escalation_scan()
    ensure_work_orders_csv_schema()

    if not os.path.exists(WORK_ORDERS_CSV):
        print("\nSUPERVISOR QUEUE: (no work_orders.csv found yet)\n")
        return

    with open(WORK_ORDERS_CSV, "r", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    active_statuses = ("OPEN", "IN_PROGRESS", "BREACHED")
    active = [r for r in rows if (r.get("Status", "").strip().upper() in active_statuses)]

    for r in active:
        r["_sla"] = _safe_int(r.get("SLA_Minutes"), 999999)
        r["_pr"] = priority_rank(r.get("Priority"))
        r["_age"] = _age_minutes(r.get("Created_Timestamp", ""))
        r["_breached"] = 0 if r.get("Status", "").strip().upper() == "BREACHED" else 1

    active.sort(key=lambda r: (r["_breached"], r["_pr"], r["_sla"], -r["_age"] if r["_age"] >= 0 else 999999))

    print("\nSUPERVISOR DISPATCH QUEUE (OPEN / IN_PROGRESS / BREACHED)")
    print("-" * 92)
    if not active:
        print("No active work orders. ✅")
        print("-" * 92)
        return

    print(f"{'WO_ID':<10} {'PRIORITY':<7} {'STATUS':<10} {'SLA':<6} {'AGE':<6} {'FAULT':<26} {'FLAG'}")
    print("-" * 92)

    for r in active[:limit]:
        wo = (r.get("WO_ID") or "")[:10]
        pr = (r.get("Priority") or "")[:7]
        st = (r.get("Status") or "")[:10]
        sla = str(r.get("SLA_Minutes") or "").strip() or "-"
        age = r["_age"]
        age_str = f"{age}m" if age >= 0 else "-"
        fault = (r.get("Fault") or "")[:26]
        flag = "⚠ SLA BREACH" if st.upper() == "BREACHED" else ""
        print(f"{wo:<10} {pr:<7} {st:<10} {sla:<6} {age_str:<6} {fault:<26} {flag}")

    print("-" * 92)
    print("Tip: Type Q at any prompt to view this queue.\n")


# ----------------------------
# FAULT SIMULATION
# ----------------------------
def simulate_fault():
    f = random.choice(FAULTS)
    severity = random.choice(f["severities"])
    return f["name"], severity


# ----------------------------
# TECHNICIAN ACTION MENU
# ----------------------------
def technician_action_menu(fault: str, severity: str):
    if fault == "Motor Overload":
        actions = [
            ("Reset overload relay and restart motor", True),
            ("Ignore fault and continue running", False),
            ("Replace sensor (incorrect)", False),
        ]
    elif fault == "Sensor Failure":
        actions = [
            ("Check wiring and replace sensor", True),
            ("Restart motor (incorrect)", False),
            ("Ignore alarm", False),
        ]
    elif fault == "E-stop Triggered":
        actions = [
            ("Inspect safety circuit and reset E-stop", True),
            ("Bypass E-stop (unsafe)", False),
            ("Ignore alarm", False),
        ]
    elif fault == "Power Outage":
        actions = [
            ("Verify power supply and restore service", True),
            ("Replace sensor (incorrect)", False),
            ("Ignore outage", False),
        ]
    elif fault == "Communication Error":
        actions = [
            ("Check network connection and reboot equipment", True),
            ("Replace motor (incorrect)", False),
            ("Ignore fault", False),
        ]
    elif fault == "Motor Stalling":
        actions = [
            ("Diagnose load/binding and reset motor", True),
            ("Ignore stall", False),
            ("Replace sensor (incorrect)", False),
        ]
    elif fault == "Sensor Calibration Error":
        actions = [
            ("Recalibrate sensor and validate readings", True),
            ("Restart PLC blindly", False),
            ("Ignore fault", False),
        ]
    elif fault == "Power Surge":
        actions = [
            ("Check UPS/power source and stabilize equipment", True),
            ("Ignore surge", False),
            ("Replace sensor (incorrect)", False),
        ]
    else:
        actions = [
            ("Perform standard troubleshooting steps", True),
            ("Ignore fault", False),
            ("Replace random part (incorrect)", False),
        ]

    while True:
        print("\nTECHNICIAN ACTION REQUIRED")
        print(f"Fault: {fault} ({severity})\n")
        for i, (text, _) in enumerate(actions, start=1):
            print(f"{i}. {text}")

        choice = input("\nEnter action number (or Q for supervisor queue): ").strip()

        if choice.lower() == "q":
            supervisor_queue_view()
            continue

        try:
            idx = int(choice) - 1
            selected_action, is_correct = actions[idx]
        except:
            selected_action, is_correct = ("Invalid choice → No action taken", False)

        return selected_action, is_correct


# ----------------------------
# SCORING
# ----------------------------
def compute_grade(accuracy: int) -> str:
    if accuracy >= 90:
        return "A"
    if accuracy >= 80:
        return "B"
    if accuracy >= 70:
        return "C"
    return "D"


def update_accuracy_and_grade():
    total = score["correct"] + score["incorrect"]
    score["accuracy"] = int((score["correct"] / total) * 100) if total > 0 else 0
    score["grade"] = compute_grade(score["accuracy"])


# ----------------------------
# ESCALATION RULES (SAFETY)
# ----------------------------
def apply_escalation_rules(severity: str, result: str) -> str:
    escalation = "None"

    if result == "INCORRECT":
        status_flags["escalations"] += 1
        if severity == "Critical":
            status_flags["critical_wrong"] += 1
            escalation = "AUTO ESCALATE: SAFETY / SUPERVISOR"
        else:
            escalation = "ESCALATE: SUPERVISOR NOTIFY"

    if status_flags["critical_wrong"] >= 2:
        status_flags["site_status"] = "STOP WORK"
    elif status_flags["escalations"] >= 3:
        status_flags["site_status"] = "WATCH"
    else:
        # do not force NORMAL here; SLA scan may bump to WATCH/STOP WORK
        pass

    return escalation


# ----------------------------
# HANDLE FAULT
# ----------------------------
def handle_fault(fault: str, severity: str):
    selected_action, is_correct = technician_action_menu(fault, severity)

    if is_correct:
        time_taken = 2 if severity == "Minor" else 5 if severity == "Major" else 7
        resolution = f"Correct Action: {selected_action}"
        result = "CORRECT"
    else:
        time_taken = 8 if severity == "Major" else 12
        resolution = f"Incorrect Action: {selected_action} → Escalation Required"
        result = "INCORRECT"

    escalation = apply_escalation_rules(severity, result)
    return resolution, time_taken, result, escalation, selected_action


# ----------------------------
# LOGGING (UTF-8 SAFE)
# ----------------------------
def write_text_log(entry: dict):
    with open(FAULT_LOG_TXT, "a", encoding="utf-8") as log_file:
        log_file.write(
            f"{entry.get('timestamp')} | "
            f"{entry.get('fault')} ({entry.get('severity')}) | "
            f"{entry.get('result')} | "
            f"{entry.get('escalation')} | "
            f"{entry.get('resolution')} | "
            f"Time: {entry.get('repair_time_min', 'N/A')} min\n"
        )


# ----------------------------
# WORK ORDER STATUS UPDATE PROMPT
# ----------------------------
def prompt_work_order_status_update(wo_id: str) -> None:
    while True:
        print("\nWORK ORDER CREATED:", wo_id)
        print("Update status now?")
        print("1. Start Work  (set to IN_PROGRESS)")
        print("2. Close Work  (set to CLOSED + notes)")
        print("3. Leave Open  (keep OPEN)")
        choice = input("\nEnter choice (or Q for supervisor queue): ").strip()

        if choice.lower() == "q":
            supervisor_queue_view()
            continue

        if choice == "1":
            update_work_order_row(wo_id, {"Status": "IN_PROGRESS", "Last_Updated": now_iso()})
            print(f"{wo_id} updated → IN_PROGRESS")
            return

        if choice == "2":
            notes = input("Close-out notes (what was done?): ").strip()
            update_work_order_row(wo_id, {
                "Status": "CLOSED",
                "Last_Updated": now_iso(),
                "Closed_Timestamp": now_iso(),
                "Closeout_Notes": notes,
            })
            print(f"{wo_id} updated → CLOSED")
            return

        update_work_order_row(wo_id, {"Last_Updated": now_iso()})
        print(f"{wo_id} left OPEN")
        return


# ----------------------------
# WORK ORDER GENERATOR
# ----------------------------
def generate_work_order(entry: dict):
    if entry.get("escalation") == "None":
        return None

    ensure_work_orders_csv_schema()

    wo_id = next_work_order_id()
    priority = severity_to_priority(entry.get("severity"))
    sla = priority_to_sla_minutes(priority)
    status = "OPEN"

    safe_ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    wo_filename = f"work_order_{wo_id}_{safe_ts}.txt"

    created_ts = entry.get("timestamp") or now_iso()

    with open(wo_filename, "w", encoding="utf-8") as wo:
        wo.write("MAINTENANCE WORK ORDER\n")
        wo.write("=" * 60 + "\n\n")
        wo.write(f"WORK ORDER ID: {wo_id}\n")
        wo.write(f"Status: {status}\n")
        wo.write(f"Priority: {priority}\n")
        wo.write(f"SLA: {sla} minutes\n\n")

        wo.write(f"Created: {created_ts}\n")
        wo.write(f"Fault: {entry.get('fault')}\n")
        wo.write(f"Severity: {entry.get('severity')}\n")
        wo.write(f"Result: {entry.get('result')}\n")
        wo.write(f"Escalation: {entry.get('escalation')}\n")
        wo.write(f"Site Status: {entry.get('site_status')}\n\n")

        wo.write("Technician Notes:\n")
        wo.write(f"- Action Taken: {entry.get('resolution')}\n")
        wo.write(f"- Repair Time Estimate: {entry.get('repair_time_min')} min\n\n")

        wo.write("Dispatch / Follow-Up:\n")
        wo.write("- Supervisor review required\n")
        wo.write("- Verify safety compliance\n")
        wo.write("- Schedule corrective maintenance\n\n")

        wo.write("Tools Checklist:\n")
        wo.write("- Multimeter\n")
        wo.write("- Lockout/Tagout Kit\n")
        wo.write("- Replacement parts if needed\n\n")

        wo.write("=" * 60 + "\n")
        wo.write("END OF WORK ORDER\n")

    append_work_order_to_queue({
        "WO_ID": wo_id,
        "Created_Timestamp": created_ts,
        "Fault": entry.get("fault"),
        "Severity": entry.get("severity"),
        "Priority": priority,
        "Status": status,
        "SLA_Minutes": sla,
        "Result": entry.get("result"),
        "Escalation": entry.get("escalation"),
        "Site_Status": entry.get("site_status"),
        "Technician_Action": entry.get("resolution"),
        "Repair_Time_Min": entry.get("repair_time_min"),
        "Work_Order_File": wo_filename,
        "Last_Updated": now_iso(),
        "Closed_Timestamp": "",
        "Closeout_Notes": "",
        "Breach_Reason": "",
    })

    prompt_work_order_status_update(wo_id)

    # SLA scan + queue view after status update
    supervisor_queue_view()

    return wo_filename


# ----------------------------
# CSV EXPORTS + REPORT
# ----------------------------
def export_fault_history_csv():
    with open(FAULT_HISTORY_CSV, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            "Timestamp",
            "Fault",
            "Severity",
            "Result",
            "Escalation",
            "Resolution",
            "Repair_Time_Min",
            "Total_Repair_Time_Min",
            "Total_Downtime_Sec",
            "Accuracy_Pct",
            "Grade",
            "Site_Status",
            "Work_Order_File",
        ])

        for e in event_history:
            writer.writerow([
                e.get("timestamp"),
                e.get("fault"),
                e.get("severity"),
                e.get("result"),
                e.get("escalation"),
                e.get("resolution"),
                e.get("repair_time_min"),
                e.get("total_repair_time_min"),
                e.get("total_downtime_sec"),
                e.get("accuracy_pct"),
                e.get("grade"),
                e.get("site_status"),
                e.get("work_order_file"),
            ])


def generate_report():
    with open(REPORT_TXT, "w", encoding="utf-8") as report:
        report.write("End-of-Day Fault Simulation Report\n")
        report.write("=" * 60 + "\n\n")

        report.write("Fault Count:\n")
        for fault, count in fault_count.items():
            report.write(f"{fault}: {count} occurrences\n")

        report.write("\nTotals:\n")
        report.write(f"Total repair time: {total_repair_time} minutes\n")
        report.write(f"Total downtime (between faults): {total_downtime_seconds} seconds\n")

        report.write("\nTechnician Performance:\n")
        report.write(f"Correct actions: {score['correct']}\n")
        report.write(f"Incorrect actions: {score['incorrect']}\n")
        report.write(f"Accuracy: {score['accuracy']}%\n")
        report.write(f"Grade: {score['grade']}\n")

        report.write("\nEscalations / Status:\n")
        report.write(f"Escalations (safety): {status_flags['escalations']}\n")
        report.write(f"Critical wrong actions: {status_flags['critical_wrong']}\n")
        report.write(f"SLA breaches: {status_flags['sla_breaches']}\n")
        report.write(f"HIGH SLA breaches: {status_flags['high_sla_breaches']}\n")
        report.write(f"Site status: {status_flags['site_status']}\n")

        report.write("\n" + "=" * 60 + "\n")
        report.write("End of Report\n")


# ----------------------------
# MAIN
# ----------------------------
def main():
    global total_repair_time, total_downtime_seconds, last_event

    ensure_work_orders_csv_schema()

    print("Starting Alarm and Troubleshooting Simulator...\n")
    print("Tip: Type Q at prompts to view the Supervisor Dispatch Queue.\n")

    for _ in range(10):
        fault, severity = simulate_fault()
        resolution, time_taken, result, escalation, _selected_action = handle_fault(fault, severity)

        fault_count[fault] += 1
        total_repair_time += time_taken

        if result == "CORRECT":
            score["correct"] += 1
        else:
            score["incorrect"] += 1

        update_accuracy_and_grade()

        entry = {
            "timestamp": now_iso(),
            "fault": fault,
            "severity": severity,
            "result": result,
            "escalation": escalation,
            "resolution": resolution,
            "repair_time_min": time_taken,
            "total_repair_time_min": total_repair_time,
            "total_downtime_sec": total_downtime_seconds,
            "accuracy_pct": score["accuracy"],
            "grade": score["grade"],
            "site_status": status_flags["site_status"],
            "work_order_file": None,
        }

        write_text_log(entry)
        wo_file = generate_work_order(entry)
        entry["work_order_file"] = wo_file

        last_event = {
            "fault": fault,
            "severity": severity,
            "result": result,
            "escalation": escalation,
            "resolution": resolution,
            "time_taken_min": time_taken,
        }

        event_history.append(entry)

        # SLA scan on each cycle so site status reflects queue health
        sla_breach_escalation_scan()

        show_dashboard(
            fault_count,
            total_repair_time,
            total_downtime_seconds,
            last_event,
            score=score,
            status_flags=status_flags,
        )

        delay = random.randint(3, 7)
        total_downtime_seconds += delay
        time.sleep(delay)

        if status_flags["site_status"] == "STOP WORK":
            print("\nSTOP WORK triggered due to escalation conditions.")
            break

    generate_report()
    export_fault_history_csv()

    print("\nSimulation complete — updated files:")
    print(f"- {FAULT_LOG_TXT}")
    print(f"- {FAULT_HISTORY_CSV}")
    print(f"- {REPORT_TXT}")
    print(f"- {WORK_ORDERS_CSV} (work order queue)")
    print(f"- {COUNTER_FILE} (persistent WO counter)\n")

    supervisor_queue_view()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        generate_report()
        export_fault_history_csv()
        print("\nStopped early — files updated.")
        supervisor_queue_view()
