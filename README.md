# Field Service Fault Dispatch Simulator
## 🎥 Demo Video  
📺 Click here to watch: [Field Service Fault Dispatch Simulator Walkthrough](https://www.loom.com/share/784677200d2444aebda10b26d36b98c0)

A Python-based simulator that models real-world **field service troubleshooting and dispatch operations**, including technician fault decision-making, escalation workflows, supervisor queue management, persistent work order tracking, and maintenance-style reporting.

Built to reflect workflows commonly used in:

- Industrial automation  
- Robotics field service  
- Telecom/RF maintenance  
- Electronics troubleshooting  
- CMMS-style dispatch environments  

---

## 🚀 Project Overview

Field service teams respond to constant incoming faults: equipment alarms, breakdowns, escalations, and time-sensitive service-level agreements (SLAs).

This simulator recreates that environment by allowing a technician to:

- Process faults step-by-step  
- Escalate unresolved issues  
- Generate persistent work orders  
- Track service response timing  
- View supervisor dispatch queues  
- Export logs and CSV reports  

---

## ✅ Key Features

- **Technician Fault Decision-Making**  
  Resolve faults, escalate issues, or request additional support

- **Persistent Work Order IDs**  
  Work orders remain consistent across sessions for realistic tracking

- **Escalation Workflow**  
  Unresolved faults automatically route into escalation handling

- **Supervisor Dispatch Queue View (`Q`)**  
  Supervisors can view active escalations and pending dispatch items

- **Maintenance Logging + CSV Export**  
  Generates structured outputs for reporting and audit documentation

----

# 📸 Screenshots (GitHub Rendered)
![Supervisor Queue](https://raw.githubusercontent.com/nazin88/field-service-fault-dispatch-simulator/main/screenshots/supervisor_queue.png)

![Technician Prompt](https://raw.githubusercontent.com/nazin88/field-service-fault-dispatch-simulator/main/screenshots/technician_prompt.png)

![Work Order](https://raw.githubusercontent.com/nazin88/field-service-fault-dispatch-simulator/main/screenshots/work_order.png)


---
 

---

## ⚙️ How the Simulator Works

1. A fault is generated and assigned a unique **Work Order ID**
2. The technician responds with an action:
   - Resolve  
   - Escalate  
   - Request parts/support  
3. Escalated work orders appear in the supervisor queue (`Q`)
4. All actions are logged for traceability
5. CSV exports simulate real maintenance reporting

---

## ▶️ Run Locally

Clone the repository and run:

```bash
python app.py
