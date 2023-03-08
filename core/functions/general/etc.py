import logging
from datetime import datetime
from multiprocessing import cpu_count, Process
from random import choice
from string import ascii_letters, digits
from threading import active_count, Thread, Timer
from time import localtime, strftime
from typing import Callable, Tuple

# Enable logging
logger = logging.getLogger(__name__)


def delay(secs: int, target: Callable, args: list = None) -> bool:
    # Call a function with delay
    result = False

    try:
        t = Timer(secs, target, args)
        t.daemon = True
        result = t.start() or True
    except Exception as e:
        logger.warning(f"Delay error: {e}", exc_info=True)

    return result


def get_current_time_label() -> str:
    # Get the current time label
    return strftime("%Y%m%d%H%M%S", localtime())


def get_readable_time(secs: int = 0, the_format: str = "%Y%m%d%H%M%S") -> str:
    # Get a readable time string
    result = ""

    try:
        if secs:
            result = datetime.utcfromtimestamp(secs).strftime(the_format)
        else:
            result = strftime(the_format, localtime())
    except Exception as e:
        logger.warning(f"Get readable time error: {e}", exc_info=True)

    return result


def get_message_id() -> str:
    # Get a message id
    return f"{get_current_time_label()}-{random_str(16)}"


def get_processes_number() -> int:
    if cpu_count() <= 2:
        result = 1
    elif cpu_count() < 16:
        result = cpu_count() // 2
    else:
        result = 8
    return result


def process_daemon(target: Callable, args: Tuple, threaded: bool = False) -> None:
    # Process daemon
    if threaded:
        thread(target=process_for_threaded, args=(target, args), daemon=True)
    else:
        p = Process(target=target, args=args)
        p.daemon = True
        p.start()


def process_for_threaded(target: Callable, args: Tuple) -> None:
    p = Process(target=target, args=args)
    p.daemon = False
    p.start()
    p.join()


def random_str(i: int) -> str:
    # Get a random string
    return "".join(choice(ascii_letters + digits) for _ in range(i))


def thread(target: Callable, args: Tuple, kwargs: dict = None, daemon: bool = True) -> bool:
    # Call a function using thread
    result = False

    try:
        t = Thread(target=target, args=args, kwargs=kwargs, daemon=daemon, name=f"{target.__name__}-{random_str(8)}")
        t.daemon = daemon
        result = t.start() or True
    except Exception as e:
        logger.warning(f"Thread error: {e}", exc_info=True)
        logger.warning(f"Current threads: {active_count()}")

    return result
