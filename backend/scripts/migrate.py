import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy import text

import backend.app.models  # noqa: F401 - Ensure all models are registered in Base.metadata
from backend.app.database import Base, engine


def run_migrations(target_engine=None):
    eng = target_engine or engine
    print(f"Applying database schema migrations on {eng.url.database}...")
    Base.metadata.create_all(bind=eng)
    with eng.connect() as conn:
        conn.execute(text("ALTER TABLE returns ADD COLUMN IF NOT EXISTS claimed_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;"))
        conn.execute(text("ALTER TABLE returns ADD COLUMN IF NOT EXISTS claimed_at TIMESTAMP;"))
        conn.execute(text("ALTER TABLE returns ADD COLUMN IF NOT EXISTS claim_expires_at TIMESTAMP;"))
        conn.execute(text("ALTER TABLE returns ADD COLUMN IF NOT EXISTS assigned_driver_id INTEGER REFERENCES users(id) ON DELETE SET NULL;"))
        # Convert legacy USD currency values to INR (rate 80) if existing
        conn.execute(text("""
            UPDATE cost_estimates
            SET estimated_resale_value = estimated_resale_value * 80,
                estimated_repair_cost = estimated_repair_cost * 80,
                estimated_transport_cost = estimated_transport_cost * 80,
                estimated_packaging_cost = estimated_packaging_cost * 80,
                estimated_sanitization_cost = estimated_sanitization_cost * 80,
                estimated_nrv = estimated_nrv * 80
            WHERE estimated_resale_value > 0 AND estimated_resale_value < 1000;
        """))
        conn.execute(text("""
            UPDATE processing_tasks
            SET actual_repair_cost = actual_repair_cost * 80,
                actual_packaging_cost = actual_packaging_cost * 80,
                actual_labor_cost = actual_labor_cost * 80,
                actual_transport_cost = actual_transport_cost * 80,
                total_actual_cost = total_actual_cost * 80
            WHERE total_actual_cost > 0 AND total_actual_cost < 1000;
        """))
        conn.execute(text("""
            UPDATE dispositions
            SET realized_resale_value = realized_resale_value * 80
            WHERE realized_resale_value > 0 AND realized_resale_value < 1000;
        """))
        conn.commit()
    print("All tables and migrations applied successfully!")

def reset_database(target_engine=None):
    eng = target_engine or engine
    print(f"Resetting schema on {eng.url.database}...")
    Base.metadata.drop_all(bind=eng)
    Base.metadata.create_all(bind=eng)
    print("Database reset and re-created successfully!")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
        reset_database()
    else:
        run_migrations()
