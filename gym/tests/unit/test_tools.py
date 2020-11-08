import logging
import unittest
import asyncio
import os
import json

from gym.common.tools import Tools

logger = logging.getLogger(__name__)


class TestTools(unittest.TestCase):
    async def run_probers(self):
        folder_path = os.path.join(os.path.dirname(__file__), "../../agent/probers")

        tools = Tools()
        tools_cfg = {
            "folder": folder_path,
            "prefix": "prober_",
            "suffix": "py",
            "full_path": True,
        }

        await tools.load(tools_cfg)

        actions = [
            {
                "id": 1,
                "instance": 1,
                "name": "ping",
                "args": {
                    "packets": 2,
                    "target": "1.1.1.1",
                },
                "sched": {
                    "from": 0,
                    "until": 14,
                    "duration": 0,
                    "interval": 2,
                    "repeat": 2,
                },
            },
            {
                "id": 2,
                "name": "ping",
                "instance": 1,
                "args": {
                    "packets": 2,
                    "target": "127.0.0.1",
                },
                "sched": {
                    "from": 0,
                    "until": 0,
                    "duration": 0,
                    "interval": 0,
                    "repeat": 2,
                },
            },
        ]

        reply = await tools.handle(actions)
        logger.debug(json.dumps(reply, sort_keys=True, indent=4))
        return reply

    def test_probers_sched(self):
        """Runs example of tools handler on probers
        Interacts with ping prober ("id":2 in each action)
        Realizes two actions, each with its own sched parameters
        """
        tools_outputs = asyncio.run(self.run_probers())
        logger.debug(len(tools_outputs))
        assert len(tools_outputs) == 4

    async def run_listeners(self):
        folder_path = os.path.join(os.path.dirname(__file__), "../../monitor/listeners")

        tools = Tools()
        tools_cfg = {
            "folder": folder_path,
            "prefix": "listener_",
            "suffix": "py",
            "full_path": True,
        }

        await tools.load(tools_cfg)

        actions = [
            # {
            #     "id": 1,
            #     "instance": 1,
            #     "name": "docker",
            #     "args": {"target": "hammurabi", "duration": "3",},
            # },
            {
                "id": 2,
                "name": "host",
                "instance": 1,
                "args": {"duration": "3"},
                "sched": {
                    "from": 0,
                    "until": 0,
                    "duration": 0,
                    "interval": 0,
                    "repeat": 2,
                },
            },
        ]

        reply = await tools.handle(actions)
        logger.debug(json.dumps(reply, sort_keys=True, indent=4))
        return reply

    def test_listeners_sched(self):
        tools_outputs = asyncio.run(self.run_listeners())
        logger.debug(len(tools_outputs))
        assert len(tools_outputs) == 2


if __name__ == "__main__":
    # unittest.main()

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(threadName)s %(name)s %(message)s",
    )
    t = TestTools()
    t.test_listeners_sched()
