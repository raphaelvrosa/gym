import logging
import unittest
import asyncio
import os
import json

from gym.common.tools import Tools


logger = logging.getLogger(__name__)


class TestTools(unittest.TestCase):
    async def run_tools(self):
        folder_path = os.path.join(os.path.dirname(__file__), "../../agent/probers")

        tools = Tools()
        tools_cfg = {
            "folder": folder_path,
            "prefix": "prober_",
            "suffix": "py",
            "full_path": True,
        }

        await tools.load(tools_cfg)

        actions = {
            1: {
                "id": 2,
                "args": {"packets": None, "target": "8.8.8.8",},
                "sched": {
                    "from": 0,
                    "until": 14,
                    "duration": 0,
                    "interval": 2,
                    "repeat": 2,
                },
            },
            2: {
                "id": 2,
                "args": {"packets": 3, "target": "1.1.1.1",},
                "sched": {
                    "from": 5,
                    "until": 10,
                    "duration": 10,
                    "interval": 0,
                    "repeat": 0,
                },
            },
        }

        reply = await tools.handle(actions)
        logger.debug(json.dumps(reply, sort_keys=True, indent=4))
        return reply

    def test_tools_sched(self):
        """Runs example of tools handler on probers
        Interacts with ping prober ("id":2 in each action)
        Realizes two actions, each with its own sched parameters       
        """
        # [{'id': 1, 'metrics': {'rtt_min': {'name': 'rtt_min', 'scalar': 21.163, 'type': 'float', 'unit': 'ms'}, 'rtt_avg': {'name': 'rtt_avg', 'scalar': 23.232, 'type': 'float', 'unit': 'ms'}, 'rtt_max': {'name': 'rtt_max', 'scalar': 26.994, 'type': 'float', 'unit': 'ms'}, 'rtt_mdev': {'name': 'rtt_mdev', 'scalar': 2.253, 'type': 'float', 'unit': 'ms'}, 'frame_loss': {'name': 'frame_loss', 'scalar': 0.0, 'type': 'float', 'unit': '%'}}}, {'id': 1, 'metrics': {'rtt_min': {'name': 'rtt_min', 'scalar': 22.313, 'type': 'float', 'unit': 'ms'}, 'rtt_avg': {'name': 'rtt_avg', 'scalar': 52.383, 'type': 'float', 'unit': 'ms'}, 'rtt_max': {'name': 'rtt_max', 'scalar': 136.783, 'type': 'float', 'unit': 'ms'}, 'rtt_mdev': {'name': 'rtt_mdev', 'scalar': 48.751, 'type': 'float', 'unit': 'ms'}, 'frame_loss': {'name': 'frame_loss', 'scalar': 0.0, 'type': 'float', 'unit': '%'}}}, {'id': 2, 'metrics': {'rtt_min': {'name': 'rtt_min', 'scalar': 126.244, 'type': 'float', 'unit': 'ms'}, 'rtt_avg': {'name': 'rtt_avg', 'scalar': 154.848, 'type': 'float', 'unit': 'ms'}, 'rtt_max': {'name': 'rtt_max', 'scalar': 219.048, 'type': 'float', 'unit': 'ms'}, 'rtt_mdev': {'name': 'rtt_mdev', 'scalar': 34.183, 'type': 'float', 'unit': 'ms'}, 'frame_loss': {'name': 'frame_loss', 'scalar': 0.0, 'type': 'float', 'unit': '%'}}}]

        tools_outputs = asyncio.run(self.run_tools())
        assert len(tools_outputs) == 3


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(threadName)s %(name)s %(message)s",
    )
    unittest.main()
