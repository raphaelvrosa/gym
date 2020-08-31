import logging
from datetime import datetime

from gym.common.tool import Tool


logger = logging.getLogger(__name__)


class Prober(Tool):
    """A prober is a Tool that must implement the probe
    function.

    Arguments:
        Tool {class} -- Establishes the core behavior of a Prober that 
        is defined by the Tool.main function
    """

    def __init__(self, id, name, parameters, metrics):
        Tool.__init__(self, id, name, parameters, metrics)
        self._type = "prober"

    def probe(self, settings):
        opts = settings.get("opts")
        timeout = settings.get("timeout", None)

        cmd = [self._command, *opts]
        self._call = " ".join(cmd)

        results = self._processor.start_process(self._call, timeout)
        return results
