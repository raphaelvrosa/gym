import os
import json
import logging
import asyncio
from datetime import datetime


logger = logging.getLogger(__name__)


class Loader:
    def __init__(self):
        self._files = []

    def _get_filepath(self, root, filename, full_path):
        """Adds filepath (if relative or not) to self._files list

        Arguments:
            root {string} -- Root folder where filename is located
            filename {string} -- Name of the file listed in root
            full_path {bool} -- Flag for absolute file path or not
        """

        if full_path:
            p = os.path.join(root, filename)
            file_path = os.path.abspath(p)
            self._files.append(file_path)
        else:
            self._files.append(filename)

    def _load_file(self, root, f, prefix, suffix, full_path):
        """Checks file suffix and prefix to add to files loaded

        Arguments:
            root {string} -- Root dir in file path
            f {string} -- Filename
            prefix {string} -- Prefix needed for filename
            suffix {string} -- Suffix needed for filename
            full_path {bool} -- If absolute or realtive file path must be loaded
        """
        prefix_ok = f.startswith(prefix) if prefix else True
        suffix_ok = f.endswith(suffix) if suffix else True

        if prefix_ok and suffix_ok:
            self._get_filepath(root, f, full_path)
        else:
            pass
            # logger.debug(f"Could not get file {f} path by suffix {suffix} or prefix {prefix}")

    def files(self, folder=None, prefix=None, suffix=None, full_path=False):
        """Gets all the names of files in a folder (not subfolders)

        Keyword Arguments:
            folder {string} -- Path to the folder name (default: {None})
            prefix {string} -- Filter files that begin with prefix (default: {None})
            suffix {string} -- Filter files that end with suffix (default: {None})
            full_path {bool} -- If files should be in full/abs or relative path (default: {False})

        Returns:
            [list] -- All the file names inside a folder
        """
        logger.debug(
            f"Loading files in folder {folder} - "
            f"prefix {prefix} and suffix {suffix} - full/abs path {full_path}"
        )

        for root, _, files in os.walk(folder):
            for f in files:
                self._load_file(root, f, prefix, suffix, full_path)
            break

        logger.debug(f"Loaded files: {self._files}")
        return self._files


class Handler:
    def _parse(self, call):
        """_parse a call to a command to be executed as a python process
        
        Arguments:
            call {string} -- A string containing the file to be called and its arguments
        
        Returns:
            string -- Attached cmd prefix into the call to run it as python3.7 executable
        """
        cmd = ["python3.8"]

        if type(call) is list:
            fields = [str(c) for c in call]
        else:
            fields = call.split(" ")

        cmd.extend(fields)
        cmd_str = " ".join(cmd)
        return cmd_str

    async def _call(self, cmd):
        """Performs the async execution of cmd in a subprocess
        
        Arguments:
            cmd {string} -- The full command to be called in a subprocess shell
        
        Returns:
            dict -- The output of the cmd execution containing stdout and stderr fields
        """

        logger.debug(f"Calling subprocess command: {cmd}")
        out = {}
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await proc.communicate()

            out = {
                "stdout": stdout,
                "stderr": stderr,
            }

        except OSError as excpt:
            logger.debug(f"Could not call cmd {cmd} - exception {excpt}")

            out = {
                "stdout": None,
                "stderr": proc.exception(),
            }
        except asyncio.CancelledError:
            logger.debug("cancel_me(): call task cancelled")
            raise

        finally:
            return out

    def _check_finish(self, uid, finish, timeout):
        """Checks if task has reached timeout
        
        Arguments:
            uid {string} -- Unique identifier of task
            finish {int} -- Time in seconds that task must end
            timeout {int} -- Time in seconds that task is taking
        
        Returns:
            bool -- A flag True if timeout is bigger than finish, False otherwise
        """
        if finish == 0:
            pass
        else:
            if finish <= timeout:
                logger.debug(f"Task {uid} finish timeout {timeout}")
                return True
            else:
                logger.debug(f"Task {uid} timeout {timeout}")
        return False

    async def _check_task(self, uid, task, duration):
        """Checks task if finished to obtain output result
        
        Arguments:
            uid {string} -- Unique identifier of call
            task {coroutine} -- Task coroutine of command call uid
            duration {int} -- Expected duration of task
        
        Returns:
            int -- Amount of time in seconds that task took to be executed
        """
        if duration != 0:
            logger.debug(f"Waiting for task {uid} duration")
            await asyncio.sleep(duration)
            logger.debug(f"Task {uid} duration ended")
            task_duration = duration
        else:
            logger.debug(f"Waiting for task {uid} (normal execution)")
            start = datetime.now()
            _, _ = await asyncio.wait({task})
            stop = datetime.now()
            task_duration = (stop - start).total_seconds()

        return task_duration

    async def _check_task_result(self, uid, task):
        """Retrieves task output result 
        
        Arguments:
            uid {string} -- Unique identifier of task/call
            task {coroutine} -- Task coroutine of command call uid
        
        Returns:
            dict -- Output of task command executed by call
        """
        logger.debug(f"Checking Task {uid}")
        if task.done():
            logger.debug(f"Result Task {uid} Done")
            result = task.result()
        else:
            logger.debug(f"Cancel Task {uid} Pending")
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                logger.debug(f"Task {uid} cancelled")
            finally:
                result = None

        return result

    async def _schedule(self, uid, cmd, sched):
        """Executes a call uid to the command cmd following the
        scheduling (time) properties of sched
        
        Arguments:
            uid {string} -- The call unique id
            cmd {string} -- The command to be called/executed
            sched {dict} -- Contains keys that determine the timely manner
            that the cmd is going to be called
        
        Returns:
            list -- A list of results of the called cmd according to sched parameters
        """
        logger.debug(f"Scheduling call uid {uid}")
        logger.debug(f"Schedule parameters: {sched}")
        loop = asyncio.get_event_loop()
        results = []

        begin = sched.get("from", 0)
        finish = sched.get("until", 0)
        duration = sched.get("duration", 0)
        repeat = sched.get("repeat", 0)
        interval = sched.get("interval", 0)

        timeout = 0
        task_duration = 0
        repeat = 1 if repeat == 0 else repeat

        for _ in range(repeat):

            await asyncio.sleep(begin)
            begin = interval

            task = loop.create_task(self._call(cmd))
            logger.debug(f"Task {uid} created {task}")

            task_duration = await self._check_task(uid, task, duration)
            result = await self._check_task_result(uid, task)

            if result:
                logger.debug(f"Task {uid} result available")
                results.append(result)
            else:
                logger.debug(f"Task {uid} result unavailable")

            timeout += task_duration + interval
            if self._check_finish(uid, finish, timeout):
                break

        return results

    async def _build(self, calls):
        """Builds list of command calls as coroutines to be
        executed by asyncio loop
        
        Arguments:
            calls {list} -- List of command calls
        
        Returns:
            list -- Set of coroutines scheduled to be called
        """
        logger.debug(f"Building calls into coroutines")
        aws = []
        for uid, (call, call_sched) in calls.items():
            cmd = self._parse(call)
            aw = self._schedule(uid, cmd, call_sched)
            aws.append(aw)

        return aws

    async def run(self, calls):
        """Executes the list of calls as coroutines
        returning their results
        
        Arguments:
            calls {list} -- Set of commands to be scheduled and called as subprocesses
        
        Returns:
            dict -- Results of calls (stdout/stderr) indexed by call uid
        """
        results = {}

        aws = await self._build(calls)

        logger.debug(f"Running built coroutines")
        tasks = await asyncio.gather(*aws, return_exceptions=True)

        calls_ids = list(calls.keys())
        counter = 0

        for aw in tasks:
            uid = calls_ids[counter]

            if isinstance(aw, Exception):
                logger.debug(f"Could not run _schedule {calls[uid]} - exception {aw}")
            else:
                results[uid] = aw

            counter += 1

        return results

    async def run_serial(self, calls):
        """Executes each call listed in calls in series
        
        Arguments:
            calls {list} -- List of calls to be run in sequence
        
        Returns:
            dict -- Results of calls (stdout/stderr) indexed by call uid
        """
        outputs = {}

        for uuid, call in calls.items():
            cmd = self._parse(call)
            logger.debug(f"Running {cmd}")
            output = await self._call(cmd)
            outputs[uuid] = output

        return outputs


class Tools:
    def __init__(self):
        self.loader = Loader()
        self.handler = Handler()
        self._cfg = {}
        self._files = {}
        self._info = {}

    def cfg(self, config):
        """Configures the parameters to load and execute the tool filenames
        
        Arguments:
            config {dict} -- Contains all the parameters needed to list and execute the files
            If all the config parameters were present in config, it loads those items in self._cfg
        """
        keys = ["folder", "prefix", "suffix", "full_path"]
        if all([True if k in config else False for k in keys]):
            self._cfg = {k: v for k, v in config.items() if k in keys}

    async def load(self, config):
        """Uses parameters configured in self.cfg() to load the tools into:
        - self._files (dict of tools file paths listed by Loader indexed by tool id)
        - self._info (dict of info of tools extracted with Handler indexed by tool id)
        """

        self.cfg(config)
        files = self.loader.files(**self._cfg)

        calls = {key: [files[key], "--info"] for key in range(len(files))}

        logger.debug(f"Loading tools info")
        outputs = await self.handler.run_serial(calls)

        for uuid, out in outputs.items():
            stdout = out.get("stdout", None)

            if stdout:
                info = json.loads(stdout)
                self._files[info["id"]] = files[uuid]
                self._info[info["id"]] = info
            else:
                expt = out.get("stderr", {})
                logger.debug(
                    f"Could not get info from {files[uuid]} - exception {expt}"
                )

        tools_names = [tool.get("name") for tool in self._info.values()]
        logger.info(f"Tools loaded: {tools_names}")

        logger.debug(f"Tools full info: {self._info}")

    def info(self):
        """Gets the information of tools after listed and loaded
        their information (executed with flag --info)
        
        Returns:
            dict -- Info of each tool indexed by its unique identifier extracted
            after executing the file path of the tool using the flag --info
            e.g., /usr/bin/python3.7 /path/to/probers/prober_ping.py --info
        """
        return self._info

    def __build_calls(self, actions):
        """Builds calls of actions into a dict of commands
        Uses identifier of each tool (via the self._files dict) to 
        build the call with the command (tool file path) and its arguments
        (list of parameters prefixed by '--')
        
        Arguments:
            actions {dict} -- Set of actions in the form of, for instance:
            1: -> Call unique identifier
            {
                'id': 2, -> Unique identifier of the tool to be called
                'args': { -> Arguments to be used when calling the tool
                    'packets': 4,
                    'target': '8.8.8.8',
                },
                'sched': { -> parameters to schedule the call of the tool
                    "from": 0,
                    "until": 14,
                    "duration": 0,
                    "interval": 2,
                    "repeat": 2
            },
        
        Returns:
            dict -- A set of calls to be executed, parameterized by the
            call unique identifier, and with the values of a tuple containing
            the parsed action command and its scheduling parameters
        """

        logger.info("Building actions into calls")
        calls = {}

        for uid, action in actions.items():
            act_id = action.get("id")

            if act_id in self._files:
                act_args = action.get("args")

                call_file = self._files.get(act_id)
                call_args = [
                    "--" + key + " " + str(value) for key, value in act_args.items()
                ]

                call = [call_file]
                call.extend(call_args)
                call_sched = action.get("sched", {})
                calls[uid] = (call, call_sched)

            else:
                logger.info(
                    f"Could not locate action id {act_id}"
                    f" into set of tools {self._files.keys()}"
                )

        return calls

    def __extract_metrics(self, uid, out):
        """Extract metrics from list of output results
        of call execution when stdout was generated
        
        Arguments:
            uid {string} -- Unique identifier of call
            out {list} -- Set of stdout produced by executed call
        
        Returns:
            dict -- Set of metrics (indexed by name) and call unique identifier
        """
        metrics = {}

        for metric in out.get("metrics"):
            name = metric.get("name")
            metrics[name] = metric

        out = {
            "id": uid,
            "metrics": metrics,
        }

        return out

    def __parse_stdout(self, uid, stdout):
        """Parses output of called commands 
        
        Arguments:
            uid {string} -- Unique identifier of call
            stdout {string} -- Json-like output of called command
        
        Returns:
            dict -- Loaded output of called command containing the metrics
            and the unique identifier of the call
        """
        out = {}

        try:
            out = json.loads(stdout)

        except Exception as e:
            logger.info(f"Could not parse result of call {uid} stdout - exception {e}")
            out = {}
        else:
            # out = self.__extract_metrics(uid, out)
            out["id"] = uid
            logger.debug(f"Parsed result of call {uid} stdout")

        finally:
            return out

    def __parse_stderr(self, uid, stderr):
        try:
            err = json.loads(stderr)
        except Exception as e:
            logger.info(f"Could not parse stderr of call {uid} - exception {e}")
            err = {}
        else:
            logger.debug(f"Parsed stderr result of call {uid} - stderr {err}")
            err = {"id": uid, "error": err}
        finally:
            return err

    def __parse_result(self, uid, result):
        """Parse result of call identified by uid
        
        Arguments:
            uid {string} -- Unique identifier of call
            result {string} -- Output of the call command
        
        Returns:
            tuple -- (output,error): if correct parsing of output
            error is None, else error contains exception in parsing
            output is None in this case, or correct parsed result of
            result parsing
        """
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")

        out, err = {}, {}

        if stdout:
            out = self.__parse_stdout(uid, stdout)

        else:
            err = self.__parse_stderr(uid, stderr)
            logger.debug(f"Could not run instruction {uid} - error {err}")

        return out, err

    def __build_outputs(self, results):
        """Parses all the ouputs of results of list of calls executed
        
        Arguments:
            results {dict} -- Set of calls results indexed by call unique identifier
        
        Returns:
            list -- Set of outputs of calls that were successfully executed
        """
        outputs = []

        for uid, result_list in results.items():
            outs = []
            for result in result_list:
                out, err = self.__parse_result(uid, result)

                if err:
                    logger.info(f"Error in call {uid} executed")
                    outs.append(err)
                else:
                    logger.info(f"Call {uid} successfully executed")
                    outs.append(out)

            outputs.extend(outs)

        return outputs

    async def handle(self, actions):
        """Handles actions to be executed by scheduled calls and 
        properly parsed into output results
        
        Arguments:
            actions {dict} -- Set of actions indexed by unique identifiers
        
        Returns:
            dict -- Set of each action execution output
            indexed by action unique identifier
        """
        logger.info("Started handling instruction actions")
        calls = self.__build_calls(actions)
        results = await self.handler.run(calls)
        outputs = self.__build_outputs(results)
        logger.info(f"Finished handling instruction actions")
        # logger.debug(f"{outputs}")
        return outputs
