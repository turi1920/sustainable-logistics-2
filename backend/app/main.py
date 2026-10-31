from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import auth, inspection, organizations, retailer, returns, warehouse
from backend.app.database import Base, engine

# Create database tables if not existing
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sustainable Reverse Logistics API",
    description="Backend API for managing end-to-end circular reverse logistics workflows, role-based operations, recovery estimates, and auditability.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(returns.router)
app.include_router(warehouse.router)
app.include_router(inspection.router)
app.include_router(retailer.router)
app.include_router(organizations.router)

@app.get("/health")
@app.get("/api/v1/health")
def health_check():
    return {
        "status": "healthy",
        "service": "sustainable-reverse-logistics-api",
        "version": "2.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
