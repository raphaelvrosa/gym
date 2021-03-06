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

    def start_process(self, args, timeout=None):
        """Run a process using the provided args
        if stop is true it waits the timeout specified
        before stopping the process, otherwise waits till
        the process stops

        Arguments:
            args {str} -- A process command to be called via shell

        Keyword Arguments:
            timeout {int} -- The time in seconds to wait before
            stopping the process.

        Returns:
            dict -- (int, string, string) The return code of the 
            process, its stdout and its stderr (both formated in json)
        """

        code, out, err = 0, "", ""
        logger.info(f"Running local process {args} - timeout {timeout}")

        try:
            result = subprocess.run(
                args, check=False, shell=True, capture_output=True, timeout=timeout,
            )
            logger.info(f"Process {result}")

            code = result.returncode
            out = result.stdout.decode("utf-8")
            err = result.stderr.decode("utf-8")

        except Exception as e:
            code = -1
            err = e
        finally:
            results = {
                "code": code,
                "out": out,
                "err": err,
            }
            logger.info(f"Process status {results}")
            return results


class Parser:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="Tool")

    def _set_args(self, params, default):
        """Defines which arguments a parser must contain

        Arguments:
            params {list} -- Set of params that will the input of a tool
            when its command is called
            default {list} -- Default parameters (to be called upon every tool)
        """
        if params:
            for param in params:
                arg = "--" + param
                self.parser.add_argument(arg, action="store", required=False)

        if default:
            for param in default:
                arg = "--" + param
                self.parser.add_argument(arg, action="store_true", required=False)

    def parse(self, params=None, default=None):
        """Defines the parameter arguments of a parser
        and parses the argv fields accordingly. It is used
        for every tool when it is called to execute an action or
        return its info.

        Keyword Arguments:
            params {list} -- Set of params that will the input of a tool
            when its command is called (default: {None})
            default {list} -- Default parameters (to be called upon every tool)
            (default: {None})

        Returns:
            dict -- The arguments parsed into a dict with the provided
            values
        """
        self._set_args(params, default)
        args = self.parser.parse_args()
        kwargs = dict(args._get_kwargs())
        return kwargs


class Tool:
    DEFAULT_PARAMS = {"info": "info"}

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
        self._default = Tool.DEFAULT_PARAMS
        self._argparser = Parser()
        self._processor = Processor()

    def parser(self, results):
        """Must be implemented for every tool

        Arguments:
            results {dict} -- The raw results of a tool
            command being called, which must be converted
            into a proer list of metrics format.

        Raises:
            NotImplementedError: If the tool does not implement this
        """
        raise NotImplementedError("Method parser not implemented for tool")

    def format_metrics(self, metrics):
        logger.info("Formating metrics")
        try:
            format_metrics = {m.get("name"): m for m in metrics if m.get("name", None)}
            logger.info("Metrics formated")

        except Exception as e:
            logger.info(f"Error formating metrics - exception {repr(e)}")
            format_metrics = []
        finally:
            return format_metrics

    def format(self, results):
        metrics, error = [], ""

        try:
            raw_metrics, error = self.parser(results)
        except Exception as e:
            error = repr(e)
        else:
            metrics = self.format_metrics(raw_metrics)
        finally:
            return metrics, error

    def info(self):
        """A default call used to extract
        the tool information as the dict returned

        Returns:
            dict -- Basic info about a tool
            so it can be called using certain parameters
            and expect certain metrics in return
        """
        inf = {
            "id": self.id,
            "name": self.name,
            "parameters": self.parameters,
            "metrics": self.metrics,
        }
        return inf

    def source(self):
        """Contains info about the tool
        that will compose the source of the
        output metrics of the tool call

        Returns:
            dict -- As below
        """
        source = {
            "id": self.id,
            "type": self._type,
            "name": self.name,
            "call": self._call,
        }
        return source

    def timestamp(self):
        """Builds a dict indicating the
        time when the tool started and stopped
        its execution

        Returns:
            dict -- As below
        """
        ts = {
            "start": self._tstart,
            "stop": self._tstop,
        }
        return ts

    def output(self, results):
        """Format the output metrics into a dict
        containing the needed info for a snapshot

        Arguments:
            results {tuple} (metrics {list}, error {str}) -- Set of metrics output
            of a tool execution (probe/listen), and the error (if existent)

        Returns:
            dict -- Formated output fo the tool call
        """

        (metrics, error) = results
        output = {
            "error": error,
            "metrics": metrics,
            "timestamp": self.timestamp(),
            "source": self.source(),
        }
        return output

    def probe(self, settings):
        """A prober must implement this
        function call interface

        Arguments:
            settings {dict} -- Params for the 
            prober call

        Raises:
            NotImplementedError: Every prober
            must implement this
        """
        raise NotImplementedError("Method probe must be implemented in Prober")

    def listen(self, settings):
        """A listener must implement this
        function call interface

        Arguments:
            settings {dict} -- Params for the
            listener call

        Raises:
            NotImplementedError: Every listener
            must implement this
        """
        raise NotImplementedError("Method listen must be implemented in Listener")

    def run(self, settings):
        """Executes the tool call

        Arguments:
            settings {dict} -- Parsed, serialized, and
            properly handle options that compose the settings
            that a tool must use to run its action and return
            its results
            It records the timestamp of the execution, when
            it started and stopped, to be included in the 
            output snapshot content

        Returns:
            dict -- Results of the output of the tool executed
            command, i.e., a prober or listener call
        """
        self._tstart = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        try:
            if self._type == "prober":
                results = self.probe(settings)
            if self._type == "listener":
                results = self.listen(settings)

        except Exception as e:
            logger.info(f"Run tool exception - {repr(e)}")
            results = {"err": repr(e)}

        else:
            logger.info(f"Run tool successful")

        self._tstop = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return results

    def options(self, opts):
        """Must be implemented by the child classes
        It must interpret the parsed options into
        the command args that will be used to call the tool

        Arguments:
            opts {dict} -- Parsed and serialized args

        Raises:
            NotImplementedError: Raises if it is not implemented
            by a child class
        """
        raise NotImplementedError

    def run_default(self, default):
        """Executes the tool default calls

        Arguments:
            default {dict} -- Contains possible 
            calls to default parameters of the tool
            e.g., info makes the info() function to be called

        Returns:
            dict -- Contains the output of the default
            options called
        """
        output = {}

        default_functions = {"info": self.info}

        for function_name in default:
            default_call = default_functions.get(function_name, {})

            if default_call:
                call_output = default_call()
                output.update(call_output)

        return output

    def serialize(self, args):
        """Serialized the parsed args into the 
        parameters that the tool will use to call
        its command (process or probe/listen)

        Arguments:
            args {dict} -- Parsed args

        Returns:
            tuple -- (dict, dict)
            The options serialized according to the tool
            parameters;
            The default tool parameters (so far just info),
            by default if any default parameter is provided it
            takes precedence over the other parameters when 
            the tool is called.
        """
        args_filter = {key: value for (key, value) in args.items() if value}

        options = {
            self.parameters[k]: v
            for k, v in args_filter.items()
            if k in self.parameters
        }

        default = {k: v for k, v in args_filter.items() if k in self._default}

        if not options:
            if not default:
                default = {"info": "info"}

        return options, default

    def args(self):
        """Parses the provided sys argv arguments of the 
        tool call and returns the serialized options that will
        compose the tool process.

        Returns:
            dict -- The parsed args according to the parser
            set parameters and default arguments
        """
        args = self._argparser.parse(params=self.parameters, default=self._default)

        return args

    def main(self):
        """Implements the whole lifecycle of a tool:
        Parse the provided args
        Run the tool according to the parse args
        Returns a json with the output of the tool ran based on provided args

        Returns:
            string -- A JSON of the tool output from 
            its execution based on the provided arguments (sys argv)
        """
        args = self.args()
        options, default = self.serialize(args)

        if default:
            output = self.run_default(default)
        else:
            settings = self.options(options)
            results = self.run(settings)
            formated = self.format(results)
            output = self.output(formated)

        json_output = json.dumps(output, sort_keys=True, indent=4)
        return json_output
