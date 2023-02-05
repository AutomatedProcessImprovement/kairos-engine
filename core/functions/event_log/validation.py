import logging

from fastapi import HTTPException

from core.enums.definition import ColumnDefinition

# Enable logging
logger = logging.getLogger(__name__)


def validate_column_definition(column_definition: dict[str, ColumnDefinition | None]) -> bool:
    """Validate a column definition.

    Args:
        column_definition (dict[str, ColumnDefinition | None]): A column definition.

    Returns:
        bool: True if the column definition is valid, False otherwise.
    """
    if not any(d == ColumnDefinition.CASE_ID for d in column_definition.values()):
        raise HTTPException(status_code=400, detail="No case ID column found")
    if not any(d == ColumnDefinition.ACTIVITY for d in column_definition.values()):
        raise HTTPException(status_code=400, detail="No activity column found")
    if (not (has_timestamp := any(d == ColumnDefinition.TIMESTAMP for d in column_definition.values()))
            and not any(d == ColumnDefinition.START_TIMESTAMP for d in column_definition.values())
            and not any(d == ColumnDefinition.END_TIMESTAMP for d in column_definition.values())):
        raise HTTPException(status_code=400, detail="No timestamp column found")
    if not has_timestamp and not all(d in column_definition.values()
                                     for d in [ColumnDefinition.START_TIMESTAMP, ColumnDefinition.END_TIMESTAMP]):
        raise HTTPException(status_code=400, detail="Invalid column definition")
    return True
