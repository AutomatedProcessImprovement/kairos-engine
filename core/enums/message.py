from enum import Enum


class MessageType(str, Enum):
    """Enum for message type."""
    ONLINE_INQUIRY = "ONLINE_INQUIRY"
    ONLINE_REPORT = "ONLINE_REPORT"
    TRAINING_DATA = "TRAINING_DATA"
    DATA_REPORT = "DATA_REPORT"
    ERROR_REPORT = "ERROR_REPORT"
    TRAINING_START = "TRAINING_START"
    MODEL_NAME = "MODEL_NAME"
    ONGOING_DATASET = "ONGOING_DATASET"
    STREAMING_PREPARE = "STREAMING_PREPARE"
    STREAMING_READY = "STREAMING_READY"
    PRESCRIPTION_REQUEST = "PRESCRIPTION_REQUEST"
    PRESCRIPTION_RESULT = "PRESCRIPTION_RESULT"
    STREAMING_STOP = "STREAMING_STOP"
