from fastapi import APIRouter, Query
from app.api.dependencies import CurrentUser, TransactionSession
from app.api.contracts import IdentifierPath
from app.schemas.notifications import NotificationResponse
from app.services.notifications import NotificationService

router = APIRouter(prefix='/notifications', tags=['Notifications'])


@router.get('', response_model=list[NotificationResponse])
def list_notifications(user: CurrentUser, session: TransactionSession,
                       offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    return NotificationService(session).list(user.id, offset=offset, limit=limit)


@router.get('/unread-count')
def unread_count(user: CurrentUser, session: TransactionSession):
    return {'count': NotificationService(session).unread_count(user.id)}


@router.patch('/read-all')
def read_all(user: CurrentUser, session: TransactionSession):
    return {'updated': NotificationService(session).read_all(user.id)}


@router.patch('/{notification_id}/read', response_model=NotificationResponse)
def read_one(notification_id: IdentifierPath, user: CurrentUser, session: TransactionSession):
    return NotificationService(session).read_one(user.id, notification_id)
