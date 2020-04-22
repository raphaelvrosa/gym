import logging
import json
import argparse
import subprocess
import time
from datetime import datetime


logger = logging.getLogger(__name__)


class Processor:
    def __init__(self):
        self._process = None

    def _parse(self, out, err):
        output = out.decode('UTF-8')
        error = err.decode('UTF-8')
        return output, error

    def start_process(self, args, stop=False, timeout=60):
        code, out, err = 0, {}, {}

        try:
            p = subprocess.Popen(args,
                stdin = subprocess.PIPE,
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE,
                )
            self._process = p

            if stop:
                if self.stop_process(timeout):
                    out, err = p.communicate()
                    out, err = self._parse(out, err)
                    code = p.returncode
                else:    
                    code = -1
        
            else:
                out, err = p.communicate()
                out, err = self._parse(out, err)
                code = p.returncode

        except OSError as e:
            code = -1
            err = e
        finally:
            self._process = None
            return code, out, err

    def stop_process(self, timeout):
        if self._process:
            time.sleep(timeout)
            self._process.kill()
            return True
        return False


class Parser:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description='Tool')

    def _set_args(self, params, default):
        if params:
            for param in params:
                arg = '--' + param
                self.parser.add_argument(arg,
                                        action="store",
                                        required=False)

        if default:
            for param in default:
                arg = '--' + param
                self.parser.add_argument(arg, 
                                        action="store_true",
                                        required=False)

    def parse(self, params=None, default=None):
        self._set_args(params, default)
        args = self.parser.parse_args()
        kwargs = dict(args._get_kwargs())
        return kwargs


class Tool:
    PARAMS = {
        "info": "info"
    }

    def __init__(self, id, name, parameters, metrics):
        self.id = id
        self.name = name
        self.parameters = parameters
        self.metrics = metrics
        self._command = None
        self._call = None
        self._type = None
        self._tstart = None
        self._tstop = None
        self._default = Tool.PARAMS
        self._parser = Parser()
        self._processor = Processor()

    def parser(self, results):
        raise NotImplementedError

    def info(self):
        inf = {k:v for k, v in self.__dict__.items() if k[:1] != '_'}
        return inf
        
    def source(self):
        source = {
            "id": self.id,
            "type": self._type,
            "name": self.name,
            "call": self._call,
        }
        return source

    def timestamp(self):
        ts = {
            "start": self._tstart,
            "stop": self._tstop,
        }
        return ts

    def output(self, metrics):
        output = {
            "metrics": metrics, 
            "timestamp": self.timestamp(),
            "source": self.source(),
        }
        return output

    def probe(self, settings):
        raise NotImplementedError

    def listen(self, settings):
        raise NotImplementedError

    def run(self, settings):
        self._tstart = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        if self._type == "prober":
            results = self.probe(settings)
        elif self._type == "listener":
            results = self.listen(settings)
        else:
            results = {}

        self._tstop = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ')

        return results

    def options(self, opts):
        raise NotImplementedError

    def run_default(self, default):
        if "info" in default:
            output = self.info()
        else:
            output = {}
        return output 

    def serialize(self, args):
        options = {}
        default = {}
        args_filter = {key:value for (key, value) in args.items() if value}

        for k, v in args_filter.items():
            if k in self.parameters:
                option_name = self.parameters[k]
                options[option_name] = v
            elif k in self._default:
                default[k] = v
            else:
                logger.info(f"Serialize option {k} not found in params "
                            f"{ {**self.parameters, **self._default} }")

        return options, default

    def args(self):
        args = self._parser.parse(params=self.parameters, default=self._default)
        return args

    def main(self):
        args = self.args()
        options, default = self.serialize(args)

        if default:
            output = self.run_default(default)
        else:
            settings = self.options(options)
            results = self.run(settings)
            metrics = self.parser(results)
            output = self.output(metrics)

        json_output = json.dumps(
            output, sort_keys=True, indent=4
        )
        return json_output
