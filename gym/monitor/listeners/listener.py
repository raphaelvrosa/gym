import logging
from datetime import datetime

from gym.common.tool import Tool


logger = logging.getLogger(__name__)


class Listener(Tool):
    """A Listener is a Tool that must implement a 
    listen function.

    Arguments:
        Tool {class} -- Establishes the core behavior of a Listener that 
        is defined by the Tool.main function
    """

    def __init__(self, id, name, parameters, metrics):
        Tool.__init__(self, id, name, parameters, metrics)
        self._type = "listener"

    def options(self, options):
        opts = []
        timeout = None

        for k, v in options.items():
            if k == "target":
                continue
            else:
                opts.extend([k, v])
        if "target" in options:
            opts.append(options["target"])

        settings = {"opts": opts, "timeout": timeout}
        return settings

    def listen(self, settings):
        opts = settings.get("opts")
        timeout = settings.get("timeout", None)

        if self._command:
            cmd = [self._command, *opts]
            self._call = " ".join(cmd)
            results = self._processor.start_process(cmd, timeout)
        else:
            opts_list = [k for j in opts.items() for k in j]
            self._call = self.__class__.__name__ + " " + " ".join(opts_list)
            results = self.monitor(opts)

        # if ret == 0:
        #     results = out
        # elif stop and ret == -9:
        #     results = out
        # else:
        #     results = {"error": err}

        return results

    def monitor(self, opts):
        results = {
            "code": 0,
            "out": "",
            "err": "",
        }
        return results
