import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.core.security import hash_password
from backend.app.database import SessionLocal
from backend.app.models.assessment import Assessment, CostEstimate
from backend.app.models.audit import ReturnStatusHistory
from backend.app.models.return_request import ReturnRequest
from backend.app.models.user import Organization, User
from backend.app.services.recovery_policy_service import generate_recovery_options


def seed_demo_data(target_session=None, reset=False):
    db: Session = target_session or SessionLocal()
    try:
        if reset:
            print("Cleaning existing demo data...")
            db.query(ReturnStatusHistory).delete()
            db.query(CostEstimate).delete()
            db.query(Assessment).delete()
            db.query(ReturnRequest).delete()
            db.query(User).delete()
            db.query(Organization).delete()
            db.commit()

        print("Seeding Organizations...")
        org1 = db.query(Organization).filter(Organization.name == "TechRetail Direct").first()
        if not org1:
            org1 = Organization(id=1, name="TechRetail Direct", org_type="RETAILER", contact_email="ops@techretail.example")
            db.add(org1)

        org2 = db.query(Organization).filter(Organization.name == "Apex Mobile").first()
        if not org2:
            org2 = Organization(id=2, name="Apex Mobile", org_type="RETAILER", contact_email="returns@apexmobile.example")
            db.add(org2)

        org_platform = db.query(Organization).filter(Organization.name == "Reverse Logistics Central").first()
        if not org_platform:
            org_platform = Organization(id=3, name="Reverse Logistics Central", org_type="PLATFORM", contact_email="admin@logistics.example")
            db.add(org_platform)
        db.commit()

        print("Seeding Demo Users...")
        demo_users = [
            {
                "username": "admin",
                "email": "admin@logistics.example",
                "password": hash_password("Admin123!"),
                "full_name": "Chief Platform Admin",
                "role": "ADMIN",
                "organization_id": 3
            },
            {
                "username": "warehouse",
                "email": "warehouse@logistics.example",
                "password": hash_password("Warehouse123!"),
                "full_name": "Senior Warehouse Operator",
                "role": "WAREHOUSE",
                "organization_id": 3
            },
            {
                "username": "inspector",
                "email": "inspector@logistics.example",
                "password": hash_password("Inspector123!"),
                "full_name": "Lead Electronics Inspector",
                "role": "INSPECTOR",
                "organization_id": 3
            },
            {
                "username": "retailer_tech",
                "email": "retailer1@techretail.example",
                "password": hash_password("Retailer123!"),
                "full_name": "TechRetail Accounts Rep",
                "role": "RETAILER",
                "organization_id": 1
            },
            {
                "username": "retailer_apex",
                "email": "retailer2@apexmobile.example",
                "password": hash_password("Retailer123!"),
                "full_name": "Apex Mobile Returns Rep",
                "role": "RETAILER",
                "organization_id": 2
            }
        ]

        for u in demo_users:
            existing = db.query(User).filter(User.username == u["username"]).first()
            if not existing:
                user = User(
                    username=u["username"],
                    email=u["email"],
                    hashed_password=u["password"],
                    full_name=u["full_name"],
                    role=u["role"],
                    organization_id=u["organization_id"],
                    is_active=True
                )
                db.add(user)
        db.commit()

        print("Seeding Initial Return Cases...")
        insp_user = db.query(User).filter(User.username == "inspector").first()
        insp_id = insp_user.id if insp_user else 1

        # Return 1: TechRetail Direct (Smartphone in RETURN_REQUESTED)
        ret1 = db.query(ReturnRequest).filter(ReturnRequest.id == "RET-1001").first()
        if not ret1:
            ret1 = ReturnRequest(
                id="RET-1001",
                order_ref="ORD-TR-9001",
                organization_id=1,
                product_category="Smartphone",
                product_name="Google Pixel 7 Pro 128GB",
                sku="PXL-7P-BLK",
                serial_expected="SN-PXL-78901",
                customer_pincode="94103",
                return_reason="Intermittent touch lag, minor back scratch",
                status="RETURN_REQUESTED",
                created_at=datetime.utcnow()
            )
            db.add(ret1)
            hist1 = ReturnStatusHistory(
                return_id="RET-1001",
                old_status=None,
                new_status="RETURN_REQUESTED",
                actor_username="admin",
                actor_role="ADMIN",
                action="INITIAL_SEED",
                details="Initial demo return request"
            )
            db.add(hist1)

        # Return 2: Apex Mobile (Smartwatch in RECEIVED)
        ret2 = db.query(ReturnRequest).filter(ReturnRequest.id == "RET-1002").first()
        if not ret2:
            ret2 = ReturnRequest(
                id="RET-1002",
                order_ref="ORD-APX-8002",
                organization_id=2,
                product_category="Smartwatch",
                product_name="Apex Active 4 GPS Watch",
                sku="APX-ACT4-SLV",
                serial_expected="SN-APX-44201",
                serial_received="SN-APX-44201",
                customer_pincode="60601",
                return_reason="Battery drains quickly",
                status="RECEIVED",
                storage_location="Bin W-204",
                package_condition="Original box, light wear",
                received_at=datetime.utcnow(),
                created_at=datetime.utcnow()
            )
            db.add(ret2)
            hist2 = ReturnStatusHistory(
                return_id="RET-1002",
                old_status="RETURN_REQUESTED",
                new_status="RECEIVED",
                actor_username="warehouse",
                actor_role="WAREHOUSE",
                action="RECEIPT_CONFIRMED",
                details="Received in intake bin W-204"
            )
            db.add(hist2)

        # Return 3: TechRetail Direct (AWAITING_APPROVAL with recovery estimates)
        ret3 = db.query(ReturnRequest).filter(ReturnRequest.id == "RET-1003").first()
        if not ret3:
            ret3 = ReturnRequest(
                id="RET-1003",
                order_ref="ORD-TR-9003",
                organization_id=1,
                product_category="Smartphone",
                product_name="Apple iPhone 13 128GB Midnight",
                sku="IPH-13-128M",
                serial_expected="SN-IPH-99341",
                serial_received="SN-IPH-99341",
                customer_pincode="10001",
                return_reason="Customer upgraded",
                status="AWAITING_APPROVAL",
                storage_location="Bin W-105",
                package_condition="Intact box, all accessories",
                received_at=datetime.utcnow(),
                created_at=datetime.utcnow()
            )
            db.add(ret3)
            assess3 = Assessment(
                return_id="RET-1003",
                inspector_id=insp_id,
                physical_condition="LOW_DAMAGE",
                screen_condition="Pristine screen, micro scuffs on bezel",
                battery_health_pct=91,
                functional_tests_passed=True,
                damage_notes="Light normal cosmetic wear.",
                safety_concerns="None. Battery thermals normal."
            )
            db.add(assess3)

            # Estimates for RET-1003
            options = generate_recovery_options(
                product_category="Smartphone",
                base_resale_value=Decimal("450.00"),
                physical_condition="LOW_DAMAGE",
                battery_health=91,
                functional_passed=True
            )
            for opt in options:
                ce = CostEstimate(
                    return_id="RET-1003",
                    option_type=opt["option_type"],
                    estimated_resale_value=opt["estimated_resale_value"],
                    estimated_repair_cost=opt["estimated_repair_cost"],
                    estimated_transport_cost=opt["estimated_transport_cost"],
                    estimated_packaging_cost=opt["estimated_packaging_cost"],
                    estimated_sanitization_cost=opt["estimated_sanitization_cost"],
                    estimated_nrv=opt["estimated_nrv"],
                    is_recommended=opt["is_recommended"],
                    recommendation_reason=opt["recommendation_reason"],
                    co2_saved_kg=opt["co2_saved_kg"],
                    environmental_assumptions=opt["environmental_assumptions"]
                )
                db.add(ce)

            hist3 = ReturnStatusHistory(
                return_id="RET-1003",
                old_status="RECEIVED",
                new_status="AWAITING_APPROVAL",
                actor_username="inspector",
                actor_role="INSPECTOR",
                action="INSPECTION_COMPLETED",
                details="Inspection complete and recovery options generated"
            )
            db.add(hist3)

        db.commit()
        print("Demo database successfully seeded!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        if not target_session:
            db.close()

if __name__ == "__main__":
    reset = "--reset" in sys.argv
    seed_demo_data(reset=reset)
