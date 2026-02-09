import os
from datetime import datetime


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def format_row(label: str, value: str, width: int = 34) -> str:
    label = (label[: width - 1] + "…") if len(label) > width else label
    return f"{label:<{width}} {value}"


def show_dashboard(
    fault_count: dict,
    total_repair_time: int,
    total_downtime_seconds: int,
    last_event: dict | None,
    score: dict | None = None,
    status_flags: dict | None = None,
):
    clear_screen()

    print("FIELD SERVICE FAULT DASHBOARD")
    print("=" * 60)
    print(format_row("Status", "RUNNING"))
    print(format_row("Last update", datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    print("-" * 60)

    # Flags
    if status_flags:
        sev = status_flags.get("site_status", "NORMAL")
        escal = status_flags.get("escalations", 0)
        crit_wrong = status_flags.get("critical_wrong", 0)
        print("SITE STATUS")
        print(format_row("Plant condition", sev))
        print(format_row("Escalations", str(escal)))
        print(format_row("Critical wrong actions", str(crit_wrong)))
        print("-" * 60)

    # Last event
    print("LAST EVENT")
    if last_event:
        print(format_row("Fault", str(last_event.get("fault", "-"))))
        print(format_row("Severity", str(last_event.get("severity", "-"))))
        print(format_row("Result", str(last_event.get("result", "-"))))
        print(format_row("Escalation", str(last_event.get("escalation", "None"))))
        print(format_row("Resolution", str(last_event.get("resolution", "-"))))
        print(format_row("Repair time (min)", str(last_event.get("time_taken_min", "-"))))
    else:
        print("No events yet.")
    print("-" * 60)

    # Totals + score
    print("TOTALS")
    print(format_row("Total repair time (min)", str(total_repair_time)))
    print(format_row("Total downtime (sec)", str(total_downtime_seconds)))

    if score:
        print(format_row("Correct actions", str(score.get("correct", 0))))
        print(format_row("Incorrect actions", str(score.get("incorrect", 0))))
        print(format_row("Accuracy", f"{score.get('accuracy', 0)}%"))
        print(format_row("Technician grade", str(score.get("grade", "-"))))

    print("-" * 60)

    # Fault counts
    print("FAULT COUNTS")
    for k in sorted(fault_count.keys()):
        print(format_row(k, str(fault_count[k])))
    print("=" * 60)
    print("Tip: Press Ctrl+C in terminal to stop.")
