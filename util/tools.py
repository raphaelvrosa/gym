import sys
import os
import logging
import argparse
import subprocess
import yaml


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
            logger.debug(
                f"Could not get file {f} path by suffix {suffix} or prefix {prefix}"
            )

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

    def load(self, filepath):
        try:
            with open(filepath, "r") as fp:
                data = yaml.load(fp, Loader=yaml.FullLoader)

        except Exception as e:
            data = {}
            logger.debug(f"Could not load file {filepath} - Exception: {e}")
        else:
            logger.debug(f"Load file ok {filepath}")
        finally:
            return data


class Processor:
    def __init__(self):
        self._process = None

    def run(self, args, timeout=None):
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
                args,
                check=False,
                shell=True,
                capture_output=True,
                timeout=timeout,
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


class Config:
    def __init__(self):
        self._info = None

    def get(self):
        return self._info

    def check_tools(self, required, existent):
        ack = True

        if existent:
            ack = all([True if t in existent else False for t in required])

        return ack

    def check(self, tools=[]):
        info = {}

        if self.cfg.install:
            install_tools = list(self.cfg.install)
            ack = self.check_tools(install_tools, tools)
            if ack:
                logger.info(f"Args install: {install_tools}")
                info["install"] = install_tools

        if self.cfg.uninstall:
            uninstall_tools = list(self.cfg.uninstall)
            ack = self.check_tools(uninstall_tools, tools)
            if ack:
                logger.info(f"Args uninstall: {install_tools}")
                info["uninstall"] = uninstall_tools

        return info

    def parse(self, argv=None):

        parser = argparse.ArgumentParser(description="Gym Tools Util")

        parser.add_argument(
            "--install",
            nargs="+",
            help="Define the list of tools to install"
            "(e.g., ping, iperf3, psutil) (default: [])",
        )

        parser.add_argument(
            "--uninstall",
            nargs="+",
            help="Define the list of tools to uninstall"
            "(e.g., ping, iperf3, psutil) (default: [])",
        )

        self.cfg, _ = parser.parse_known_args(argv)
        info = self.check()

        if info:
            self._info = info
            return True

        return False


class ToolsUtil:
    def __init__(self):
        self.tools = {}
        self.config = Config()
        self.processor = Processor()
        self.loader = Loader()
        self.init()

    def init(self):
        logger.info(f"Tools Util Init")
        tools_folderpath = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "./tools")
        )

        logger.info(f"Loading tools at {tools_folderpath}")

        files = self.loader.files(
            folder=tools_folderpath, suffix=".yml", full_path=True
        )

        for f in files:
            data = self.loader.load(f)
            if data:
                tool_name = data.get("name")
                self.tools[tool_name] = data
                logger.info(f"Loaded tool {tool_name}")

    def call(self, action, tool):

        if tool in self.tools:
            logger.info(f"Calling {action} in tool {tool}")

            data = self.tools.get(tool)

            tool_install = data.get(action)

            results = []
            for cmd in tool_install:
                result = self.processor.run(cmd)
                code = result.get("code")

                if code == 0:
                    results.append(True)
                else:
                    results.append(False)

            ack_results = all(results)
            return ack_results

        else:
            logger.info(f"Fail: call {action} in tool {tool} - tool not existent")
            return False

    def main(self, info):
        acks_install = {}
        acks_uninstall = {}

        tools_install = info.get("install", [])
        tools_uninstall = info.get("uninstall", [])

        if "all" in tools_install:
            tools_install = list(self.tools.keys())

        if "all" in tools_uninstall:
            tools_uninstall = list(self.tools.keys())

        for tool in tools_install:
            ack = self.call("install", tool)
            acks_install[tool] = ack
            logger.info(f"Output of install in tool {tool}: {ack}")

        for tool in tools_uninstall:
            ack = self.call("uninstall", tool)
            acks_uninstall[tool] = ack
            logger.info(f"Output of uninstall in tool {tool}: {ack}")

        all_acks_install = all(acks_install.values())
        all_acks_uninstall = all(acks_uninstall.values())

        all_acks = all_acks_install and all_acks_uninstall

        logger.info(f"Output of install tools: {all_acks_install}")
        logger.info(f"Output of uninstall tools: {all_acks_uninstall}")
        logger.info(f"Output of actions in tools: {all_acks}")
        return all_acks

    def run(self, argv):
        ok = self.config.parse(argv)

        if ok:
            info = self.config.get()
            ack = self.main(info)

            if ack:
                logger.info("Successfuly run tools util")
                return 0
            else:
                logger.info("Some errors to run tools util")
                return -1
        else:
            logger.info("Could not run tools util")
            return -1


def logs():
    dir_name = "/tmp/gym/logs/"
    try:
        os.makedirs(dir_name)
    except OSError:
        pass

    filepath = "/tmp/gym/logs/util_tools.log"
    logging.basicConfig(filename=filepath, level=logging.DEBUG)


if __name__ == "__main__":
    logs()
    app = ToolsUtil()
    app.run(sys.argv[1:])