# ⚙️ Field Service Fault & Work Order Dispatch Simulator

Industrial automation fault response + CMMS-style work order dispatch simulator with supervisor queue, SLA breach escalation, technician scoring, and maintenance reporting.

---

## 🚀 Overview

This project simulates a **real-world industrial maintenance and automation support workflow**, where equipment faults are detected, technicians respond with corrective actions, and escalations automatically generate work orders for supervisors.

It reflects workflows used in:

- Manufacturing plants  
- Robotics field service teams  
- Industrial maintenance operations  
- Automation & controls support environments  

---

## 🔥 Core Features

### ✅ Fault Simulation + Severity Levels
Generates realistic industrial faults such as:

- Motor Overload  
- Motor Stalling  
- Power Surge  
- Communication Errors  
- Sensor Failures  
- Emergency Stop Triggered  

Each fault includes severity:

- Minor  
- Major  
- Critical  

---

### 👷 Technician Decision System
Technicians must choose the correct action for every fault.

System tracks:

- Correct vs incorrect actions  
- Safety violations  
- Technician accuracy  
- Final technician grade (A–F)

---

### 📄 CMMS-Style Work Order Generation
Incorrect or unsafe responses trigger escalation work orders with:

- Persistent IDs (`WO-000001`, `WO-000002`, …)  
- Supervisor notification requirements  
- Tool checklist + corrective follow-up steps  
- Site status + escalation notes  

Sample output files:

- `work_order_WO-000001_....txt`

---

### 📊 Supervisor Dispatch Queue View
At any technician prompt, supervisors can type:

```text
Q
