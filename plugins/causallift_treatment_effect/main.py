import logging

from core.functions.plugin.common import plugin_run, plugin_scheduler

from plugins.causallift_treatment_effect import memory
from plugins.causallift_treatment_effect.config import basic_info
from plugins.causallift_treatment_effect.handler import callback, processed_messages_clean

# Enable logging
logger = logging.getLogger(__name__)
for _ in logging.root.manager.loggerDict:
    if _.startswith("pika"):
        logging.getLogger(_).setLevel(logging.CRITICAL)


if __name__ == "__main__":
    plugin_scheduler(processed_messages_clean, memory.processed_messages)
    plugin_run(basic_info, callback)
