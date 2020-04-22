import logging
from datetime import datetime

from gym.common.tool import Tool


logger = logging.getLogger(__name__)


class Prober(Tool):
    def __init__(self, id, name, parameters, metrics):
        Tool.__init__(self, id, name, parameters, metrics)
        self._type = "prober"
       
    def probe(self, settings):
        opts = settings.get("opts") 
        stop = settings.get("stop") 
        timeout = settings.get("timeout") 
        
        cmd = [self._command, *opts]
        self._call = " ".join(cmd)

        ret, output, error = self._processor.start_process(cmd, stop, timeout)

        if ret == 0:
            results = output
        elif stop and ret == -9:
            results = output
        else:
            results = {"error": error}

        return results