import os
import json
import asyncio
import logging
import subprocess

from prompt_toolkit.shortcuts import PromptSession
from prompt_toolkit.completion import WordCompleter, NestedCompleter
from prompt_toolkit.styles import Style
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

from gym.common.vnfbr import VNFBR
from gym.cli.interfaces import GymPlayerInterface
from gym.cli.output import print_cli, format_text


logger = logging.getLogger(__name__)


class LocalPlugin:
    def execute_command(self, args, daemon=False):
        """Run a process using the provided args
        if stop is true it waits the timeout specified
        before stopping the process, otherwise waits till
        the process stops

        Arguments:
            args {list} -- A process command to be called

        Keyword Arguments:
            stop {boll} -- If the process needs to be stopped (true)
            or will stop by itself (false) (default: {False})
            timeout {int} -- The time in seconds to wait before
            stopping the process, in case stop is true (default: {60})

        Returns:
            tuple -- (int, string, string) The return code of the
            process, its stdout and its stderr (both formated in json)
        """
        code, out, err = 0, {}, {}

        try:
            logger.info(f"Running local process {args}")
            result = subprocess.run(
                args,
                check=True,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.info(f"Process Status {result}")
            code = result.returncode
            out = result.stdout
            err = result.stderr

        except Exception as e:
            logger.info(f"Process exception {repr(e)}")
            code = -1
            err = repr(e)
        finally:
            if code == 0:
                out_str = str(out) if out else "ok"
                logger.info(f"Process stdout {out_str}")
                return True, out_str
            else:
                err_str = str(err) if err else "error"
                logger.info(f"Process stderr {err_str}")
                return False, err_str


class Proxy:
    def __init__(self):
        self._plugin = LocalPlugin()

    def clone(self):
        logger.info(f"Workflow clone gym to /tmp/gym/source")

        cmd = "git clone https://github.com/raphaelvrosa/gym /tmp/gym/source"
        ack, msg = self._plugin.execute_command(cmd, daemon=False)

        logger.info(f"Stats workflow clone: {ack} - msg: {msg}")
        return ack

    def aux_visual(self, action):
        logger.info(f"Workflow visual {action}")

        self.clone()

        if action == "start":
            cmd = "cd /tmp/gym/source && make start-visual"
        elif action == "stop":
            cmd = "cd /tmp/gym/source && make stop-visual"
        else:
            cmd = None

        if cmd:
            ack, msg = self._plugin.execute_command(cmd)
            logger.info(f"Workflow {action}: visual aux component {ack} - {msg}")

    def start(self, info):
        logger.info(f"Workflow start: component {info.get('name')}")

        if info.get("sudo", False):
            sudo_cmd = "sudo ps aux | grep gym-"
            ack, msg = self._plugin.execute_command(sudo_cmd)

            cmd = "sudo gym-{name} --uuid {uuid} --address {address} --debug &".format(
                name=info.get("name"),
                uuid=info.get("uuid"),
                address=info.get("address"),
            )
        else:
            cmd = "gym-{name} --uuid {uuid} --address {address} --debug &".format(
                name=info.get("name"),
                uuid=info.get("uuid"),
                address=info.get("address"),
            )
        ack, msg = self._plugin.execute_command(cmd, daemon=True)

        logger.info(f"Stats workflow start: {ack} - msg: {msg}")
        return ack

    def stop(self, info):
        logger.info(f"Workflow stop: component {info.get('name')}")

        if info.get("sudo", False):
            cmd = "sudo pkill -9 'gym-{name}'".format(name=info.get("name"))
        else:
            cmd = "pkill -9 'gym-{name}'".format(name=info.get("name"))

        ack, msg = self._plugin.execute_command(cmd)

        logger.info(f"Stats workflow stop: {ack} - msg: {msg}")

        return ack


class CLIRunner:
    def __init__(self):
        self._infra_info = {
            "sudo": True,
            "name": "infra",
            "address": "localhost:57000",
            "uuid": "gym-infra",
        }
        self._player_info = {
            "sudo": False,
            "name": "player",
            "address": "localhost:56000",
            "uuid": "gym-player",
        }
        self.proxy = Proxy()
        self.vnfbr = None
        self.gymplayer_interface = GymPlayerInterface()
        self.cmds = {
            "load": self.load,
            "begin": self.begin,
            "end": self.end,
        }

        self._status = {
            "load": False,
            "begin": False,
            "end": False,
        }
        logger.info("CLIRunner init")

    def get_cmds(self):
        return list(self.cmds.keys())

    def filepath(self, name):
        filepath = os.path.normpath(os.path.join(os.path.dirname(__file__), name))
        return filepath

    def load_file(self, filename):
        filepath = self.filepath(filename)
        data = {}
        error = ""
        try:
            vnfbr = VNFBR()
            vnfbr.load(filepath)
        except Exception as e:
            error = f"Load file error: {repr(e)}"
            logger.debug(error)
        else:
            logger.debug(f"Load file ok")
            data = vnfbr
        finally:
            return data, error

    def load(self, filename):
        logger.info(f"Load triggered - filename {filename}")
        ack = True

        print_cli(f"Loading configuration file at {filename}")

        data, error = self.load_file(filename)

        if error:
            msg = "Configuration not loaded - " + error
            print_cli(None, err=msg, style="error")
        else:
            msg = "Configuration loaded"
            print_cli(msg, style="normal")
            self.vnfbr = data

        self._status["load"] = ack

        logger.info(f"{msg}")
        return msg

    def begin_components(self):
        logger.info(f"Begin components")
        self.proxy.start(self._player_info)
        print_cli(
            f"gym requires sudo credentials to start/stop gym-infra (i.e., Containernet)",
            style="warning",
        )
        self.proxy.start(self._infra_info)

    def end_components(self):
        logger.info(f"End components")
        self.proxy.stop(self._player_info)
        print_cli(
            f"gym requires sudo credentials to start/stop gym-infra (i.e., Containernet)",
            style="warning",
        )
        self.proxy.stop(self._infra_info)

    def save(self, result):
        ack = False
        filedir = "/tmp/gym/results/"

        vnfbr_dict = result.get("vnfbr")
        vnfbr = VNFBR()
        ack_parse = vnfbr.parse(vnfbr_dict)

        if ack_parse:
            try:
                ack = vnfbr.save(filedir=filedir, csv=True)
            except Exception as ex:
                error = f"Experiment VNF-BR save file error: {repr(ex)}"
                logger.debug(error)
            else:
                msg = f"Experiment VNF-BR save file success."
                logger.debug(msg)
                ack = True
            finally:
                if ack:
                    print_cli(
                        f"Result VNF-BR {vnfbr_dict.get('id')} (json and csv) saved to {filedir}",
                        style="normal",
                    )
                else:
                    print_cli(f"Result VNF-BR saving error", style="error")

        else:
            print_cli(
                f"Result VNF-BR parse error - could not save result", style="error"
            )

    async def begin(self):
        logger.info(f"begin triggered")

        self.begin_components()
        await asyncio.sleep(3)

        print_cli(f"Beginning", style="attention")

        print_cli(f"Experiment Begin", style="info")

        address = self._player_info.get("address")
        reply, error = await self.gymplayer_interface.call("begin", address, self.vnfbr)

        ack = False if error else True
        self._status["begin"] = ack

        if ack:
            print_cli(f"Gym Experiment Ok", style="normal")
            messages = reply
            self.save(reply)

        else:
            print_cli(f"Gym Experiment Error", style="error")
            messages = error

        logger.info(f"{messages}")
        return ack, messages

    async def end(self):
        logger.info(f"end triggered")

        print_cli(f"Ending", style="attention")

        print_cli(f"Experiment End", style="info")

        # address = self._player_info.get("address")
        # reply, error = await self.gymplayer_interface.call("end", address, self.vnfbr)
        error = None
        reply = None
        ack = False if error else True
        self._status["end"] = ack
        self._status["begin"] = not ack

        if ack:
            print_cli(f"Ended Gym Experiment", style="normal")
            messages = reply
        else:
            print_cli(f"Ended Gym Experiment Error", style="error")
            messages = error

        logger.info(f"{messages}")

        self.end_components()

        return ack, messages

    def status(self, command):
        ack = False
        error = ""

        if command == "load":
            pass

        if command == "begin":
            pass

        if command == "end":
            pass

        return True, error

    async def execute(self, cmds):
        cmd = cmds[0]
        logger.info(f"Executing commands: {cmds}")

        ok, error = self.status(cmd)

        if ok:
            available_cmds = list(self.cmds.keys())

            if cmd == "load":
                if len(cmds) == 2:
                    config_filename = cmds[1]
                    output = self.load(config_filename)
                    return output
                else:
                    return "Missing config filepath"

            if cmd in available_cmds:
                func = self.cmds.get(cmd)
                output = await func()
                return output

            else:
                output = f"Command not found in {available_cmds}"
                return output

        else:
            return error


class CLI:
    gym_completer = WordCompleter(
        ["load", "begin", "end"],
        ignore_case=True,
    )

    gym_style = Style.from_dict(
        {
            "completion-menu.completion": "bg:#008888 #ffffff",
            "completion-menu.completion.current": "bg:#00aaaa #000000",
            "scrollbar.background": "bg:#88aaaa",
            "scrollbar.button": "bg:#222222",
            "main": "#fb5607",
            "normal": "#ffd500",
            "error": "#d7263d",
            "info": "#3a86ff",
            "attention": "#8338ec",
            "warning": "#ff006e italic",
            "prompt": "#ffb300 bold",
        }
    )

    def __init__(self, args):
        self.args = args
        self.runner = CLIRunner()
        self._runner_cmds = self.runner.get_cmds()
        self.gym_completer = CLI.gym_completer
        self.update_completer()

    def update_completer(self):
        logger.info("updating cli completer")
        nested_dict = {}
        source_files = self.args.get("source", None)

        if source_files:
            logger.info(f"Updating completer with source files {source_files}")
            source_files_dict = {filepath: None for filepath in source_files}

            nested_dict = {
                "load": source_files_dict,
                "begin": None,
                "end": None,
            }

            self.gym_completer = NestedCompleter.from_nested_dict(nested_dict)

    def validator(self, text):
        words = text.split()

        if words:
            cmd = words[0]

            if cmd in self._runner_cmds:
                return words
            else:
                print(
                    f"Error: command {cmd} not available in commands {self._runner_cmds}"
                )

        return []

    def print_output(self, output):
        if type(output) is str:
            print_cli(output, style="normal")
        elif type(output) is list:
            for out in output:
                print_cli(out, style="normal")
        else:
            print_cli(f"Unkown command output format {type(output)}", style="attention")

    async def init(self):
        logger.info("CLI init")

        session = PromptSession(
            complete_while_typing=True,
            completer=self.gym_completer,
            style=CLI.gym_style,
            auto_suggest=AutoSuggestFromHistory(),
        )

        prompt = "(-: gym > "

        try:
            while True:
                try:
                    prompt_text = format_text(prompt, style="prompt")
                    text = await session.prompt_async(prompt_text)

                except KeyboardInterrupt:
                    continue
                except EOFError:
                    break

                try:
                    commands = self.validator(text)
                except Exception as e:
                    logger.debug(repr(e))
                else:

                    if commands:
                        await self.runner.execute(commands)
                        # ack, reply = await self.runner.execute(commands)

        finally:
            logger.debug("GoodBye!")
