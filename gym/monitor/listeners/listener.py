import logging
from datetime import datetime

from gym.common.tool import Tool


logger = logging.getLogger(__name__)


class Listener(Tool):
    
    def __init__(self, id, name, parameters, metrics):
        Tool.__init__(self, id, name, parameters, metrics)
        self._type = "listener"

    def options(self, options):
        opts = []
        stop = False
        timeout = 0
        for k, v in options.items():
            if k == 'target':
                continue
            else:
                opts.extend([k, v])
        if 'target' in options:
            opts.append(options['target'])

        settings = {
            "opts": opts,
            "stop": stop,
            "timeout": timeout
        }
        return settings

    def listen(self, settings):       
        opts = settings.get("opts") 
        stop = settings.get("stop") 
        timeout = settings.get("timeout")

        if self._command:
            cmd = [self._command, *opts]
            self._call = " ".join(cmd)
            ret, out, err = self._processor.start_process(cmd, stop, timeout)
        else:
            opts_list = [k for j in opts.items() for k in j]
            self._call = self.__class__.__name__ + " " + " ".join(opts_list)
            ret = 0
            err = None
            out = self.monitor(opts)

        if ret == 0:
            results = out
        elif stop and ret == -9:
            results = out
        else:
            results = {"error": err}

        return results

    def monitor(self, opts):
        ret = 0
        err = None
        out = None
        return ret, out, err