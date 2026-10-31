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

| Role | Username | Email | Password | Organization / Carrier | Permissions / Scope |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `admin@logistics.example` | `Admin123!` | Logistics Central | Full system access, registration, user management, all returns, audit trails |
| **Warehouse Employee** | `warehouse` | `warehouse@logistics.example` | `Warehouse123!` | Logistics Central | Intake receiving, serial verification, inventory restock |
| **Inspector** | `inspector` | `inspector@logistics.example` | `Inspector123!` | Logistics Central | Technical inspection, estimates, processing execution, QC & sanitization |
| **Retailer Rep 1** | `retailer_tech` | `retailer1@techretail.example` | `Retailer123!` | TechRetail Direct | Scoped strictly to TechRetail returns; approval decisions |
| **Retailer Rep 2** | `retailer_apex` | `retailer2@apexmobile.example` | `Retailer123!` | Apex Mobile | Scoped strictly to Apex Mobile returns; cannot view TechRetail cases |
| **Pickup Driver 1** | `driver_eco` | `driver@ecologix.example` | `Pickup123!` | EcoLogix Express | Scoped to EcoLogix shipments; doorstep collection & warehouse handover |
| **Pickup Driver 2** | `driver_green` | `driver@greenroute.example` | `Pickup123!` | GreenRoute 3PL | Scoped to GreenRoute shipments; doorstep collection & warehouse handover |

### Seeded 3PL Pickup & Logistics Partners

| Partner Name | Fleet Category | Service Coverage | Contact Details |
| :--- | :--- | :--- | :--- |
| **EcoLogix Express** | Electric Van (Zero-Emission) | Metro Hubs & Suburban Zones | `Rohit Sharma` (+1-800-ECO-LOGIX / `dispatch@ecologix.example`) |
| **GreenRoute 3PL** | CNG / Hybrid Cargo Van | Nationwide Regional Corridors | `Sarah Jenkins` (+1-888-GRN-ROUTE / `ops@greenroute.example`) |

---

## Dedicated Dashboards & Role-Based Access Control

1. **Platform Admin Dashboard** (`admin`):
   - **Operational Overview**: Return statistics, status distributions, and active return cases.
   - **Register New Return**: Case intake, expected serial numbers, product categorization, and 3PL assignment.
   - **User Management**: Add new users with role and organization/carrier binding, permanently delete users (revoking credentials and access from PostgreSQL), and toggle active state.
   - **Pickup Partners & Dispatch**: Register logistics carriers, delete carriers from PostgreSQL, and assign return cases with scheduled dates and special instructions.

2. **🚚 Pickup Partner Field Logistics Portal** (`driver_eco`, `driver_green`):
   - **📍 Assigned Pickups Queue**: View shipments assigned to the driver's carrier awaiting customer doorstep collection. Drivers verify package condition and serial number, transitioning the return to `IN_TRANSIT`.
   - **🚛 Active Transit & Warehouse Handover**: View packages on vehicle in-transit and record arrival and handover at the central warehouse receiving dock, transitioning `pickup_status` to `DELIVERED_TO_WAREHOUSE`.
   - **📜 Completed Manifest & Sustainability**: View historical deliveries and metrics on avoided emissions from optimized EV logistics routing.
   - **🔍 Shipment Traceability**: Full audit trail search scoped to carrier shipments.
   - **Strict Multi-Tenant Carrier Isolation**: EcoLogix drivers can never view or execute collections for GreenRoute shipments, and vice versa.

3. **Warehouse Employee Dashboard** (`warehouse`):
   - **Warehouse Intake**: Intake receiving dock inspection, physical device serial verification, and storage bin allocation (`RECEIVED`).
   - **Restock & Dispatch**: Final inventory shelf assignment and disposition recording (`RESTOCKED` or `RETURNED_TO_RETAILER`).
   - **Case Traceability**: Audit trail inspection.

4. **Electronics Inspection & Quality Dashboard** (`inspector`):
   - **Technical Inspection**: Cosmetic grading, battery health %, diagnostic checks, and NRV cost estimates.
   - **Processing & Repair**: Execution tracking with itemized actual labor and component cost logging.
   - **Quality Check & Sanitization**: NIST SP 800-88 compliance certification.

5. **Retailer Representative Portal** (`retailer_tech`, `retailer_apex`):
   - **Approval Queue**: Review economic NRV estimates and lifecycle carbon savings.
   - **Multi-Tenant Isolation**: Retailer A cannot view or approve Retailer B's returns.

---

## Platform Administration & User Management

The Platform Admin (`admin`) has dedicated tabs for operational governance:

1. **👥 User Management**:
   - **Directory**: View all registered users, roles, email addresses, and active states.
   - **Add New User**: Securely create staff or retailer accounts with bcrypt-hashed passwords and organization mapping.
   - **Remove User**: Permanently delete custom user accounts with safeguards protecting the active administrator from self-lockout and preserving core system demo accounts.
   - **Status Toggle**: Instantly activate or deactivate any account without deleting records.

2. **🚚 Pickup Partners & Dispatch**:
   - **Carrier Management**: Register and configure third-party reverse-logistics partners with fleet eco-categorization.
   - **Dispatch & Assignment**: Assign pickup carriers and schedule dates for pending return cases.
   - **Field Chain of Custody**: Track collection from customer residence through transit to warehouse intake.

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

## Phase-Wise Sequential Data Flow & Business Rules

The platform enforces strict sequential phase-wise data flow across the reverse logistics lifecycle to maintain total data consistency:

1. **Phase 1: Return Registration (`RETURN_REQUESTED`)**: An administrator or warehouse operator creates the return request with product metadata, serial expectation, and assigns an active 3PL logistics carrier (`pickup_status = "ASSIGNED"`).
2. **Phase 2: Carrier Doorstep Collection & Exception Handling (`IN_TRANSIT` / `PICKUP_FAILED` / `RESCHEDULED`)**: 
   - **Successful Pickup**: The assigned carrier driver visits customer premises, inspects physical condition, verifies serial identity, and executes physical collection. Status transitions to `IN_TRANSIT`.
   - **Pickup Failure / Field Exception**: If pickup cannot be completed (e.g. *Customer Unavailable / Door Locked*, *Customer Refused Handover*, *Serial Mismatch*, *Damaged Battery / Safety Hazard*, *Address Inaccessible*), the driver records the failure reason and cargo notes. Status transitions to `PICKUP_FAILED`.
   - **Rescheduling**: Drivers or dispatchers can reschedule failed pickups with a new target date and customer notes (`pickup_status = "RESCHEDULED"`), placing the shipment back into the active Doorstep Collection Queue.
3. **Phase 3: Warehouse Intake Gate (`RECEIVED`)**: 
   - **Gated Validation Rule**: The warehouse operator **CANNOT** confirm warehouse receipt if the product has not been successfully collected from the customer (`pickup_status in ["PENDING_ASSIGNMENT", "ASSIGNED", "PICKUP_FAILED", "RESCHEDULED"]`).
   - The backend API rejects uncollected or failed receipt attempts with `HTTP 400 Bad Request` ("Phase Sequencing Violation").
   - The frontend UI displays dynamic badges (`🟢 Ready`, `❌ Pickup Failed`, `📅 Rescheduled`, `⏳ Awaiting Pickup`), presents an explanatory error/warning banner, and disables the "Confirm Warehouse Receipt" button until the carrier has successfully collected the product (`IN_TRANSIT` or `DELIVERED_TO_WAREHOUSE`).
   - Upon physical arrival, the warehouse confirms physical serial match and allocates a storage bin (`status = "RECEIVED"`).
4. **Phase 4: Technical Diagnostics & NRV Estimation (`INSPECTED` / `AWAITING_APPROVAL`)**: An inspector conducts cosmetic grading, battery health %, and diagnostic testing. The engine computes Net Recovery Value:
   $$\text{NRV} = \text{Estimated Resale Value} - (\text{Repair Cost} + \text{Packaging} + \text{Transport} + \text{Sanitization})$$
   It also calculates avoided carbon emissions ($\text{kg CO}_2\text{e}$) and transparently displays all LCA baseline assumptions (`AWAITING_APPROVAL`).
5. **Phase 5: Retailer Commercial Authorization (`APPROVED`)**: The retailer representative reviews recovery economics and lifecycle carbon savings, approving or rejecting the disposition. Cross-retailer tenant isolation prevents accessing other retailers' records.
6. **Phase 6: Processing & Repair Execution (`PROCESSING_COMPLETED`)**: Technicians execute repair/refurbishment and record itemized actual costs (component repair, labor, packaging, transit) separately from initial estimates.
7. **Phase 7: Quality Check & Cryptographic Data Sanitization Gate (`QC_PASSED`)**: Mandatory NIST SP 800-88 cryptographic sanitization verification. Bypassing sanitization is blocked by database constraints and validation gates.
8. **Phase 8: Restocking / Disposition (`RESTOCKED` / `RETURNED_TO_RETAILER` / `COMPLETED`)**: Warehouse operator assigns inventory resale shelf or records dispatch back to retailer.
9. **Full Audit Traceability**: Every transition records actor username, role, timestamp, prior state, new state, and actionable details.

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
#   s u s t a i n a b l e - l o g i s t i c s - 2  
 