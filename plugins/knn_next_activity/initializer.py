import logging

from pandas import DataFrame

from core.functions.plugin.common import start_training

from plugins.knn_next_activity import memory
from plugins.knn_next_activity.algorithm import Algorithm

# Enable logging
logger = logging.getLogger(__name__)


def get_instance(project_id: int, plugin_id: int, training_df: DataFrame) -> Algorithm:
    # Get instance from memory
    if project_id in memory.instances:
        return memory.instances[project_id]
    # Get new instance
    instance = get_new_instance(project_id, plugin_id, training_df)
    memory.instances[project_id] = instance
    return instance


def get_new_instance(project_id: int, plugin_id: int, training_df: DataFrame) -> Algorithm:
    # Get new instance
    return Algorithm(project_id, plugin_id, training_df)


def preprocess_and_train(project_id: int, plugin_id: int, training_df: DataFrame) -> None:
    # Pre-process and train the model
    instance = get_instance(project_id, plugin_id, training_df)
    start_training(project_id, instance)
