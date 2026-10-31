# Sustainable Reverse Logistics System

An enterprise-grade, circular reverse-logistics platform built with **Python**, **FastAPI**, **PostgreSQL**, and **Streamlit**. It tracks returned consumer electronics end-to-end: from initial registration through warehouse receipt, physical & functional inspection, recovery-value assessment (NRV), multi-tenant retailer authorization, technical execution, data sanitization certification, and inventory restocking.

---

## Architecture Overview

```text
Streamlit Frontend (Port 8501)
       │ (HTTP + JWT Bearer Auth)
       ▼
FastAPI Backend (Port 8000)
 ├── Authentication & RBAC (Bcrypt + JWT)
 ├── Return Workflow & State Machine
 ├── Recovery Economics Engine (NRV Calculation)
 ├── Environmental Circularity Engine (LCA Avoided Carbon & Assumptions)
 ├── Multi-Tenant Retailer Isolation Gates
 └── Immutable Audit Trail (ReturnStatusHistory)
       │
       ▼
PostgreSQL Database (Port 5432)
```

---

## Documented Demo Accounts & Credentials

| Role | Username | Email | Password | Organization | Permissions / Scope |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `admin@logistics.example` | `Admin123!` | Logistics Central | Full system access, registration, all returns, audit trails |
| **Warehouse Employee** | `warehouse` | `warehouse@logistics.example` | `Warehouse123!` | Logistics Central | Intake receiving, serial verification, inventory restock |
| **Inspector** | `inspector` | `inspector@logistics.example` | `Inspector123!` | Logistics Central | Technical inspection, estimates, processing execution, QC & sanitization |
| **Retailer Rep 1** | `retailer_tech` | `retailer1@techretail.example` | `Retailer123!` | TechRetail Direct | Scoped strictly to TechRetail returns; approval decisions |
| **Retailer Rep 2** | `retailer_apex` | `retailer2@apexmobile.example` | `Retailer123!` | Apex Mobile | Scoped strictly to Apex Mobile returns; cannot view TechRetail cases |

---

## Quick Start Guide

### 1. Database Setup & Migrations

Ensure PostgreSQL is running locally on port `5432` with user `postgres` and password `postgres`.

Apply migrations to create all tables:
```powershell
python backend/scripts/migrate.py
```

### 2. Seed the Demo Database

Populate demo organizations, demo accounts, and baseline return cases:
```powershell
python backend/scripts/seed.py --reset
```

### 3. Start the FastAPI Backend

```powershell
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
The interactive API documentation is available at `http://127.0.0.1:8000/docs`.

### 4. Start the Streamlit Frontend

In a separate terminal:
```powershell
streamlit run frontend/app.py --server.port 8501 --server.headless true
```
Open your browser at `http://localhost:8501`.

---

## How to Safely Reset and Reseed the Demo Database

To clear and reseed the development database at any time without affecting unrelated databases:
```powershell
python backend/scripts/seed.py --reset
```

To perform a complete schema drop and recreation:
```powershell
python backend/scripts/migrate.py reset
python backend/scripts/seed.py --reset
```

---

## End-to-End Workflow & Business Rules

1. **Return Registration**: An administrator or warehouse operator registers a return case (`RETURN_REQUESTED`).
2. **Warehouse Intake**: A warehouse operator confirms package receipt, records storage bin, and verifies the physical device serial number (`RECEIVED`).
3. **Technical Inspection**: An inspector records cosmetic, display, and battery health, and validates functional diagnostics.
4. **Recovery Economics (NRV)**: The system automatically computes Net Recovery Value:
   $$\text{NRV} = \text{Estimated Resale Value} - (\text{Repair Cost} + \text{Packaging} + \text{Transport} + \text{Sanitization})$$
   It also calculates avoided carbon emissions ($\text{kg CO}_2\text{e}$) and transparently displays all LCA baseline assumptions (`AWAITING_APPROVAL`).
5. **Retailer Authorization**: The retailer representative logs in, reviews economic and environmental data, and approves or rejects the recovery plan (`APPROVED`). Retailers cannot access other retailers' data.
6. **Processing Execution**: Technicians perform repair/refurbishment and log itemized actual costs (`PROCESSING_COMPLETED`).
7. **Quality Check & Data Sanitization Gate**: Mandatory NIST SP 800-88 cryptographic sanitization check before release (`QC_PASSED`).
8. **Restocking / Return**: Warehouse operator assigns inventory location or records return dispatch (`COMPLETED`).
9. **Full Audit Traceability**: Every status change records actor, timestamp, prior state, new state, and remarks.

---

## Running Automated Tests

Run unit tests, API integration tests, security isolation tests, and browser tests:
```powershell
python -m pytest -v
```

Run code formatting and linting:
```powershell
python -m ruff check .
```
