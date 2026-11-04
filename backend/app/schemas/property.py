from datetime import datetime, timezone
from typing import Annotated, Literal
from pydantic import Field, AwareDatetime, field_validator
from .common import ContractModel, Price
Text = Annotated[str, Field(min_length=1, max_length=2000)]
class PropertyProfileInput(ContractModel):
    display_name: Annotated[str, Field(min_length=1, max_length=120)]
    capacity: Literal['OWNER','AGENT']
    share_contact: bool = False
class PropertyCreate(ContractModel):
    title: Annotated[str, Field(min_length=1, max_length=160)]
    description: Text
    category: Literal['Residential','Commercial','Land/Plots']
    price: Price
    locality: Annotated[str, Field(min_length=1, max_length=120)]
    private_address: Text
class MessageInput(ContractModel):
    message: Text
class VisitCreate(ContractModel):
    scheduled_at: AwareDatetime
    @field_validator('scheduled_at')
    @classmethod
    def future(cls,value):
        if value <= datetime.now(timezone.utc): raise ValueError('Appointment must be in the future')
        return value
class VisitAction(ContractModel):
    action: Literal['ACCEPT','REJECT','PROPOSE','ACCEPT_ALTERNATE','RECONFIRM','CANCEL']
    scheduled_at: AwareDatetime | None = None
    @field_validator('scheduled_at')
    @classmethod
    def future(cls,value):
        if value is not None and value <= datetime.now(timezone.utc): raise ValueError('Appointment must be in the future')
        return value
class ModerationInput(ContractModel):
    status: Literal['APPROVED','REJECTED','HIDDEN']
    reason: Text | None = None
    expected_updated_at: AwareDatetime | None = None
class ReportInput(ContractModel):
    reason: Literal['fake/misleading','wrong information','already sold','suspicious owner/agent','inappropriate content','other']
    explanation: Annotated[str, Field(max_length=2000)] = ''
class DispositionInput(ContractModel):
    disposition: Literal['DISMISSED','ACTIONED']
    reason: Text
    takedown: bool = False
class SaveInput(ContractModel):
    saved: bool
class LocationInput(ContractModel):
    reason: Text | None = None
