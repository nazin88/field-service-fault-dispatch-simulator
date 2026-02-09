# 🚨 Field Service Fault Dispatch Simulator

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

### 🧑‍🔧 Technician Decision System

Technicians must choose the correct corrective action for every fault.

The simulator tracks:

- Correct vs Incorrect responses  
- Technician accuracy score  
- Letter grade performance (A–F)

---

### 📊 Live Field Service Dashboard

A continuously updating terminal dashboard shows:

- Last detected fault  
- Severity level  
- Technician result  
- Escalation status  
- Repair time tracking  
- Total downtime  
- Fault count totals  

---

### 🧾 Maintenance Work Order Generation (CMMS-Style)

When a technician selects an incorrect or unsafe action, the system auto-generates a work order:

- Priority level (HIGH / MEDIUM)
- SLA target time
- Escalation flags
- Required supervisor follow-up
- Tools checklist

Work orders are saved as:

- Individual `.txt` work order files  
- Master `work_orders.csv` export  

---

### 🚨 SLA Breach Escalation

Each work order is monitored against its SLA.

If the work order exceeds the allowed response window:

- Status changes to **BREACHED**
- Supervisor queue flags the escalation
- Dispatch priority increases automatically

---

### 👨‍💼 Supervisor Dispatch Queue View

At any technician prompt, supervisors can type:

```bash
Q
