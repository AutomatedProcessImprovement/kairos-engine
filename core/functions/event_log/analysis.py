import logging

from pandas import DataFrame

from core.enums.definition import ColumnDefinition

# Enable logging
logger = logging.getLogger(__name__)


def get_brief_with_inferred_definition(df: DataFrame) -> list[list[str | int | float | bool | ColumnDefinition | None]]:
    # Get brief with inferred definition
    result = []

    try:
        result: list = df.head(5).values.tolist()
        headers = df.columns.tolist()
        result.insert(1, get_inferred_definitions(headers))
    except Exception as e:
        logger.warning(f"Get brief with inferred definition error: {e}", exc_info=True)

    return result


def get_inferred_definitions(headers: list[str]) -> list[ColumnDefinition | None]:
    # Get inferred definition
    result = []

    try:
        result = [get_inferred_definition_by_name(header) for header in headers]
    except Exception as e:
        logger.warning(f"Get inferred definition error: {e}", exc_info=True)

    return result


def get_inferred_definition_by_name(name: str) -> ColumnDefinition | None:
    # Get inferred definition by name
    return get_infer_from_standard_name(name) if is_standard_name(name) else get_infer_from_random_name(name)


def is_standard_name(name: str) -> bool:
    # Check the name is standard name
    if ":" not in name:
        return False
    if name.split(":")[0] not in ["concept", "lifecycle", "org", "time", "case"]:
        return False
    return True


def get_infer_from_standard_name(name: str) -> ColumnDefinition | None:
    # Get inferred definition from standard name
    result = None

    try:
        if name == "case:concept:name":
            result = ColumnDefinition.CASE_ID
        elif name == "concept:name":
            result = ColumnDefinition.ACTIVITY
        elif name == "time:timestamp":
            result = ColumnDefinition.TIMESTAMP
        elif name == "lifecycle:transition":
            result = ColumnDefinition.TRANSITION
        elif name == "org:resource":
            result = ColumnDefinition.RESOURCE
    except Exception as e:
        logger.warning(f"Get infer from standard name error: {e}", exc_info=True)

    return result


def get_infer_from_random_name(name: str) -> ColumnDefinition | None:
    # Get inferred definition from random name
    result = None

    try:
        if "case" in name.lower():
            result = ColumnDefinition.CASE_ID
        elif "activity" in name.lower():
            result = ColumnDefinition.ACTIVITY
        elif "timestamp" in name.lower():
            result = ColumnDefinition.TIMESTAMP
        elif "transition" in name.lower():
            result = ColumnDefinition.TRANSITION
        elif "resource" in name.lower():
            result = ColumnDefinition.RESOURCE
        elif "start" in name.lower() and "time" in name.lower():
            result = ColumnDefinition.START_TIMESTAMP
        elif "end" in name.lower() and "time" in name.lower():
            result = ColumnDefinition.END_TIMESTAMP
        elif "duration" in name.lower():
            result = ColumnDefinition.DURATION
        elif "cost" in name.lower():
            result = ColumnDefinition.COST
    except Exception as e:
        logger.warning(f"Get infer from random name error error: {e}", exc_info=True)

    return result
