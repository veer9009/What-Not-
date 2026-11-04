from datetime import datetime
from pydantic import ConfigDict
from app.schemas.common import ContractModel, DatabaseId


class NotificationResponse(ContractModel):
    model_config = ConfigDict(from_attributes=True)
    id: DatabaseId
    kind: str
    entity_type: str
    entity_id: DatabaseId
    title: str
    body: str
    created_at: datetime
    read_at: datetime | None = None
