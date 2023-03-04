import logging
import os
from datetime import datetime

import core.crud.event_log as event_log_crud
import core.crud.plugin as plugin_crud
import core.crud.project as project_crud
from core.confs import path
from core.enums.status import ProjectStatus
from core.starters import memory
from core.functions.project.simulation import stop_simulation
from core.starters.database import SessionLocal

# Enable logging
logger = logging.getLogger(__name__)


def clean_local_storage() -> bool:
    # Clean local storage, remove abandoned files
    result = False

    try:
        with SessionLocal() as db:
            saved_names = set(event_log_crud.get_all_saved_names(db))
            remove_multiple_files(saved_names, path.EVENT_LOG_RAW_PATH, "raw event log")
            df_names = set(event_log_crud.get_all_df_names(db))
            remove_multiple_files(df_names, path.EVENT_LOG_DATAFRAME_PATH, "dataframe")
            training_df_names = set(event_log_crud.get_all_training_df_names(db))
            remove_multiple_files(training_df_names, path.EVENT_LOG_TRAINING_DF_PATH, "training dataframe")
            simulation_df_names = set(event_log_crud.get_all_simulation_df_names(db))
            remove_multiple_files(simulation_df_names, path.EVENT_LOG_SIMULATION_DF_PATH, "simulation dataframe")
            model_names = set(plugin_crud.get_all_model_names(db))
            remove_multiple_files(model_names, path.PLUGIN_MODEL_PATH, "model")
        result = True
    except Exception as e:
        logger.warning(f"Clean local storage error: {e}", exc_info=True)

    return result


def remove_multiple_files(checklist: set[str], dir_path: str, file_type: str) -> None:
    need_to_remove = [f for f in os.listdir(dir_path)
                      if (os.path.isfile(os.path.join(dir_path, f))
                          and (f not in checklist and f.split(".")[0] not in checklist))]
    for f in need_to_remove:
        os.remove(os.path.join(dir_path, f))
        logger.warning(f"Remove abandoned {file_type} file: {f}")


def pop_unused_data(data: dict) -> bool:
    # Pop unused data
    result = False

    try:
        datetime_now = datetime.now()
        for data_id in list(data.keys()):
            data_unit = data.get(data_id)
            if not data_unit:
                continue
            if (datetime_now - data_unit["date"]).total_seconds() > 30 * 60:
                del data[data_id]
        result = True
    except Exception as e:
        logger.warning(f"Pop unused data error: {e}", exc_info=True)

    return result


def stop_unread_simulations() -> bool:
    # Stop unread simulations
    result = False

    try:
        datetime_now = datetime.now()
        for project_id in list(memory.simulation_start_times.keys()):
            project_datetime = memory.simulation_start_times.get(project_id)
            if not project_datetime:
                continue
            if (datetime_now - project_datetime).total_seconds() > 5 * 60:
                with SessionLocal() as db:
                    db_project = project_crud.get_project_by_id(db, project_id)
                    if not db_project:
                        continue
                    if db_project.status != ProjectStatus.SIMULATING:
                        continue
                    stop_simulation(db, db_project)
    except Exception as e:
        logger.warning(f"Stop unread simulations error: {e}", exc_info=True)

    return result
