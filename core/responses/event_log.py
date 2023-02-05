import logging
from datetime import datetime

from pandas import Timestamp
from pydantic import BaseModel

from core.enums.definition import ColumnDefinition
from core.responses.definition import DefinitionDto

# Enable logging
logger = logging.getLogger(__name__)


class EventLogDto(BaseModel):
    id: int
    created_at: datetime
    updated_at: datetime | None = None
    file_name: str
    definition: DefinitionDto | None = None

    class Config:
        orm_mode = True


class AllEventLogsResponse(BaseModel):
    message: str
    event_logs: list[EventLogDto] = []


class UploadEventLogResponse(BaseModel):
    message: str
    event_log_id: int
    columns_header: list[str]
    columns_inferred_definition: list[ColumnDefinition | None]
    columns_data: list[list[str | Timestamp | None]]


class UpdateEventLogResponse(BaseModel):
    message: str
    event_log_id: int
    received_definition: dict[str, ColumnDefinition]
    activities_count: dict[str, int]
    outcome_selections: list[ColumnDefinition]
    treatment_selections: list[ColumnDefinition]
