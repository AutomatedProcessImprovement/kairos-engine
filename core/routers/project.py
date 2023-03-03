import logging
from datetime import datetime
from time import sleep

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

import core.crud.case as case_crud
import core.crud.definition as definition_crud
import core.crud.event as event_crud
import core.crud.event_log as event_log_crud
import core.crud.project as project_crud
import core.schemas.request.project as project_request
import core.schemas.response.project as project_response
import core.schemas.project as project_schema
from core.confs import path
from core.enums.error import ErrorType
from core.enums.status import ProjectStatus
from core.functions.event_log.dataset import get_ongoing_dataset_path, get_cases_result_skeleton
from core.functions.event_log.file import get_dataframe_from_file
from core.functions.event_log.job import start_pre_processing
from core.functions.general.etc import process_daemon, random_str
from core.functions.general.file import delete_file, get_extension, get_new_path
from core.functions.general.request import get_real_ip, get_db
from core.functions.message.sender import send_ongoing_dataset_to_all_plugins, send_streaming_prepare_to_all_plugins
from core.functions.plugin.collector import get_active_plugins
from core.functions.project.simulation import stop_simulation
from core.functions.project.streaming import event_generator
from core.functions.project.validation import validate_project_definition, validate_simulation_status
from core.starters import memory
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
        raise HTTPException(status_code=400, detail=ErrorType.EVENT_LOG_NOT_FOUND)
    db_project = project_crud.get_project_by_event_log_id(db, db_event_log.id)
    if db_project:
        raise HTTPException(status_code=400, detail=ErrorType.PROJECT_EXISTED)

    # Validate the user's input
    columns_definition = db_event_log.definition.columns_definition
    positive_outcome = create_body.positive_outcome
    treatment = create_body.treatment
    positive_outcome and validate_project_definition(positive_outcome, columns_definition)
    treatment and validate_project_definition(treatment, columns_definition)

    # Create the project
    definition_crud.set_outcome_treatment_definition(
        db=db,
        db_definition=db_event_log.definition,
        outcome=create_body.positive_outcome,
        treatment=create_body.treatment,
        fast_mode=create_body.fast_mode,
        start_transition=create_body.start_transition,
        complete_transition=create_body.complete_transition,
        abort_transition=create_body.abort_transition
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


@router.get("/{project_id}", response_model=project_response.ProjectResponse)
def read_project(request: Request, project_id: int, db: Session = Depends(get_db), _: bool = Depends(validate_token)):
    logger.warning(f"Read project - from IP {get_real_ip(request)}")

    # Get the data from the database, and validate it
    db_project = project_crud.get_project_by_id(db, project_id)
    if not db_project:
        raise HTTPException(status_code=400, detail=ErrorType.PROJECT_NOT_FOUND)

    return {
        "message": "Project retrieved successfully",
        "project": db_project
    }


@router.put("/{project_id}", response_model=project_response.ProjectResponse)
def update_project(request: Request, project_id: int, update_body: project_request.BasicUpdateProjectRequest,
                   db: Session = Depends(get_db), _: bool = Depends(validate_token)):
    logger.warning(f"Update project - from IP {get_real_ip(request)}")

    # Get the data from the database, and validate it
    db_project = project_crud.get_project_by_id(db, project_id)
    if not db_project:
        raise HTTPException(status_code=400, detail=ErrorType.PROJECT_NOT_FOUND)

    # Set name or description
    db_project = project_crud.update_name_and_description(db, db_project, update_body.name, update_body.description)

    return {
        "message": "Project's basic information updated successfully",
        "project": db_project
    }


@router.put("/{project_id}/definition", response_model=project_response.CreateProjectResponse)
def update_project_definition(request: Request, project_id: int,
                              update_body: project_request.UpdateProjectRequest,
                              db: Session = Depends(get_db), _: bool = Depends(validate_token)):
    logger.warning(f"Update project definition - from IP {get_real_ip(request)}")

    # Get the data from the database, and validate it
    db_project = project_crud.get_project_by_id(db, project_id)
    if not db_project:
        raise HTTPException(status_code=400, detail=ErrorType.PROJECT_NOT_FOUND)
    elif db_project.status not in {ProjectStatus.WAITING, ProjectStatus.TRAINED, ProjectStatus.STREAMING,
                                   ProjectStatus.SIMULATING}:
        raise HTTPException(status_code=400, detail=ErrorType.PROJECT_NOT_READY)
    db_event_log = event_log_crud.get_event_log(db, db_project.event_log_id)
    if not db_event_log:
        raise HTTPException(status_code=400, detail=ErrorType.EVENT_LOG_NOT_FOUND)

    # Validate the user's input
    columns_definition = db_event_log.definition.columns_definition
    positive_outcome = update_body.positive_outcome
    treatment = update_body.treatment
    positive_outcome and validate_project_definition(positive_outcome, columns_definition)
    treatment and validate_project_definition(treatment, columns_definition)
    stop_simulation(db, db_project, True)

    # Update the project
    definition_crud.set_outcome_treatment_definition(
        db=db,
        db_definition=db_event_log.definition,
        outcome=update_body.positive_outcome,
        treatment=update_body.treatment,
        fast_mode=update_body.fast_mode,
        start_transition=update_body.start_transition,
        complete_transition=update_body.complete_transition,
        abort_transition=update_body.abort_transition
    )

    # Start the pre-processing
    project_crud.update_status(db, db_project, ProjectStatus.PREPROCESSING)
    process_daemon(start_pre_processing, (db_project.id, db_event_log.id, get_active_plugins(), True))

    return {
        "message": "Project definition updated successfully",
        "project": db_project
    }


@router.post("/{project_id}/result", response_model=project_response.ProjectResultResponse)
def get_prescription_result(request: Request, project_id: int, file: UploadFile = Form(), seperator: str = Form(","),
                            db: Session = Depends(get_db), _: bool = Depends(validate_token)):
    logger.warning(f"Get prescription result - from IP {get_real_ip(request)}")

    if not file or not file.file or (extension := get_extension(file.filename)) not in path.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=ErrorType.EVENT_LOG_INVALID)

    db_project = project_crud.get_project_by_id(db, project_id)
    if not db_project:
        raise HTTPException(status_code=400, detail=ErrorType.PROJECT_NOT_FOUND)

    temp_path = get_new_path(f"{path.TEMP_PATH}/", suffix=f".{extension}")
    with open(temp_path, "wb") as f:
        f.write(file.file.read())

    # Get dataframe from file
    df = get_dataframe_from_file(temp_path, extension, seperator)

    # Get the result skeleton
    columns = df.columns.tolist()
    columns_definition = [db_project.event_log.definition.columns_definition.get(column) for column in columns]
    cases = get_cases_result_skeleton(df, db_project.event_log.definition)
    cases_count = len(cases)
    result = {
        "message": "Prescription results generated successfully",
        "cases_count": cases_count,
        "columns": columns,
        "columns_definition": columns_definition,
        "cases": cases
    }

    # Send the result request to the plugins
    while (result_key := random_str(8)) in memory.ongoing_results:
        continue
    memory.ongoing_results[result_key] = {}
    plugins = {plugin.key: plugin.id for plugin in db_project.plugins}
    model_names = {plugin.id: plugin.model_name for plugin in db_project.plugins}
    send_ongoing_dataset_to_all_plugins(project_id, plugins, model_names, result_key, temp_path)

    # Wait for the plugins to finish prescribing
    while len(memory.ongoing_results[result_key]) < len(plugins):
        sleep(1)

    print("Start to merge the results")
    for plugin_result in memory.ongoing_results[result_key].values():
        for case_id, case_result in plugin_result.items():
            result["cases"]: dict[str, dict[str, list]]
            result["cases"][case_id]["prescriptions"].append(case_result)
    print("Finished merging the results")

    return result


@router.put("/{project_id}/simulate/start", response_model=project_response.SimulateProjectResponse)
def simulation_start(request: Request, project_id: int, db: Session = Depends(get_db),
                     _: bool = Depends(validate_token)):
    logger.warning(f"Start simulation - from IP {get_real_ip(request)}")

    # Get the data from the database, and validate it
    db_project = project_crud.get_project_by_id(db, project_id)
    validate_simulation_status(db_project, "start")

    # Start the simulation
    db_project = project_crud.update_status(db, db_project, ProjectStatus.SIMULATING)
    plugins = {plugin.key: plugin.id for plugin in db_project.plugins}
    model_names = {plugin.id: plugin.model_name for plugin in db_project.plugins}
    send_streaming_prepare_to_all_plugins(db_project.id, plugins, model_names)
    memory.simulation_projects[db_project.id] = datetime.now()
    return {
        "message": "Project simulation started successfully",
        "project_id": project_id
    }


@router.put("/{project_id}/simulate/stop", response_model=project_response.SimulateProjectResponse)
def simulation_stop(request: Request, project_id: int, db: Session = Depends(get_db),
                    _: bool = Depends(validate_token)):
    logger.warning(f"Stop simulation - from IP {get_real_ip(request)}")

    # Get the data from the database, and validate it
    db_project = project_crud.get_project_by_id(db, project_id)
    validate_simulation_status(db_project, "stop")

    # Stop the simulation
    stop_simulation(db, db_project)

    return {
        "message": "Project simulation stopped successfully",
        "project_id": project_id
    }


@router.put("/{project_id}/simulate/clear", response_model=project_response.SimulateProjectResponse)
def simulation_clear(request: Request, project_id: int, db: Session = Depends(get_db),
                     _: bool = Depends(validate_token)):
    logger.warning(f"Clear simulation - from IP {get_real_ip(request)}")

    # Get the data from the database, and validate it
    db_project = project_crud.get_project_by_id(db, project_id)
    validate_simulation_status(db_project, "clear")

    # Stop the simulation
    if db_project.status == ProjectStatus.SIMULATING:
        stop_simulation(db, db_project)

    # Remove all the cases and events belonging to the project
    event_crud.delete_all_events_by_project_id(db, db_project.id)
    case_crud.delete_all_cases_by_project_id(db, db_project.id)

    return {
        "message": "Project simulation cleared successfully",
        "project_id": project_id
    }


@router.get("/{project_id}/streaming/result")
async def streaming_result(request: Request, project_id: int, db: Session = Depends(get_db),
                           _: bool = Depends(validate_token)):
    logger.warning(f"Streaming result - from IP {get_real_ip(request)}")

    # Get the data from the database, and validate it
    db_project = project_crud.get_project_by_id(db, project_id)
    if not db_project:
        raise HTTPException(status_code=400, detail=ErrorType.PROJECT_NOT_FOUND)
    if db_project.status not in {ProjectStatus.SIMULATING, ProjectStatus.STREAMING}:
        raise HTTPException(status_code=400, detail=ErrorType.PROJECT_NOT_STREAMING)

    # Check if the project is already being read
    if project_id in memory.reading_projects:
        raise HTTPException(status_code=400, detail=ErrorType.PROJECT_ALREADY_READING)
    memory.reading_projects.add(project_id)
    memory.simulation_projects.pop(project_id, None)

    return EventSourceResponse(event_generator(request, db, project_id))


@router.get("/{project_id}/dataset/ongoing")
def download_ongoing_dataset(request: Request, project_id: int, background_tasks: BackgroundTasks,
                             db: Session = Depends(get_db), _: bool = Depends(validate_token)):
    logger.warning(f"Download ongoing dataset - from IP {get_real_ip(request)}")

    # Get the data from the database, and validate it
    db_project = project_crud.get_project_by_id(db, project_id)
    if not db_project:
        raise HTTPException(status_code=400, detail=ErrorType.PROJECT_NOT_FOUND)

    temp_path = get_ongoing_dataset_path(db_project.event_log)

    if not temp_path:
        raise HTTPException(status_code=400, detail=ErrorType.DATASET_ERROR)

    background_tasks.add_task(delete_file, temp_path)
    return FileResponse(temp_path, media_type="text/csv", filename="ongoing_dataset.csv")
