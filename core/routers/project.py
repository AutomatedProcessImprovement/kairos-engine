import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

import core.crud.definition as definition_crud
import core.crud.event_log as event_log_crud
import core.crud.project as project_crud
import core.schemas.request.project as project_request
import core.schemas.response.project as project_response
import core.schemas.project as project_schema
from core.functions.event_log.job import start_pre_processing
from core.functions.general.etc import process_daemon
from core.functions.general.request import get_real_ip, get_db
from core.functions.plugin.collector import get_active_plugins
from core.functions.project.validation import validate_project_definition
from core.security.token import validate_token

# Enable logging
logger = logging.getLogger(__name__)

# Create the router
router = APIRouter(prefix="/project")


@router.post("", response_model=project_response.CreateProjectResponse)
def create_project(request: Request, create_body: project_request.CreateProjectRequest,
                   db: Session = Depends(get_db), _: bool = Depends(validate_token)):
    logger.warning(f"Create project - from IP {get_real_ip(request)}")

    # Get the data from the database, and validate it
    db_event_log = event_log_crud.get_event_log(db, create_body.event_log_id)
    if not db_event_log:
        raise HTTPException(status_code=400, detail="No valid event log provided")
    db_project = project_crud.get_project_by_event_log_id(db, db_event_log.id)
    if db_project:
        raise HTTPException(status_code=400, detail="Project already exists for this event log")

    # Validate the user's input
    validate_project_definition(create_body.positive_outcome, db_event_log.definition.columns_definition)
    validate_project_definition(create_body.treatment, db_event_log.definition.columns_definition)

    # Create the project
    definition_crud.set_outcome_treatment_definition(
        db=db,
        db_definition=db_event_log.definition,
        outcome=create_body.positive_outcome,
        treatment=create_body.treatment,
        fast_mode=create_body.fast_mode,
        start_transition=create_body.start_transition,
        end_transition=create_body.end_transition
    )
    db_project = project_crud.create_project(
        db=db,
        project=project_schema.ProjectCreate(name=db_event_log.file_name),
        event_log_id=db_event_log.id
    )

    # Start the pre-processing
    process_daemon(start_pre_processing, (db_project.id, db_event_log.id, get_active_plugins()))
    return {
        "message": "Project created successfully",
        "project": db_project
    }


@router.get("/all", response_model=project_response.AllProjectsResponse)
def read_projects(request: Request, skip: int = 0, limit: int = 100, db: Session = Depends(get_db),
                  _: bool = Depends(validate_token)):
    logger.warning(f"Read projects - from IP {get_real_ip(request)}")
    return {
        "message": "Projects retrieved successfully",
        "projects": project_crud.get_projects(db, skip=skip, limit=limit)
    }
