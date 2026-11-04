from fastapi import APIRouter

from app.schemas.common import HealthResponse
from app.api.dependencies import TransactionSession
from fastapi import HTTPException
from sqlalchemy import text, select, func
from app.models.events import EmailOutbox

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Process health only; this does not report database readiness."""
    return HealthResponse()


@router.get('/ready')
def readiness(session: TransactionSession):
    """Storage/schema readiness and aggregate backlog, without recipient data."""
    revision = session.scalar(text('SELECT version_num FROM alembic_version'))
    if revision != '0008':
        raise HTTPException(503, 'Database schema is not ready')
    pending = session.scalar(select(func.count()).select_from(EmailOutbox).where(
        EmailOutbox.state.in_(['PENDING','LEASED'])))
    failed = session.scalar(select(func.count()).select_from(EmailOutbox).where(EmailOutbox.state=='FAILED'))
    oldest = session.scalar(select(func.min(EmailOutbox.created_at)).where(EmailOutbox.state.in_(['PENDING','LEASED'])))
    return dict(schema=revision,outbox_pending=pending,outbox_failed=failed,oldest_pending_at=oldest)
