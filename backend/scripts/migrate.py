import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.app.database import Base, engine


def run_migrations(target_engine=None):
    eng = target_engine or engine
    print(f"Applying database schema migrations on {eng.url.database}...")
    Base.metadata.create_all(bind=eng)
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
