import logging
from typing import Union

from fastapi import APIRouter, UploadFile

from core import confs, glovar
from core.models.dashboard import Dashboard
from core.models.event import Event
from core.models.identifier import get_identifier

# Enable logging
logger = logging.getLogger(__name__)

# Create the router
router = APIRouter(prefix="/case")


@router.get("/{dashboard_id}")
def find_cases(dashboard_id: int):
    # Get dashboard by dashboard_id
    with glovar.save_lock:
        for dashboard in glovar.dashboards:
            if dashboard.id == dashboard_id:
                break
        else:
            return {"message": "Dashboard not found"}

    # Get cases by dashboard
    dashboard: Dashboard

    return {"message": "Dashboard found", "cases": dashboard.current_event_log.cases}
