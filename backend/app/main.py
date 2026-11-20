from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api import rfqs, users
from app.core.clock import get_now
from app.core.config import settings
from app.core.errors import register_error_handlers
from app.db.session import get_db

app = FastAPI(title="British Auction RFQ")

app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"]
)
register_error_handlers(app)

app.include_router(users.router, prefix="/api/v1")
app.include_router(rfqs.router, prefix="/api/v1")


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "server_time": get_now()}
