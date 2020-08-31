import os
import sys
import json
import asyncio
import logging
import argparse

from google.protobuf import json_format

from grpclib.client import Channel

from gym.common.protobuf.gym_grpc import PlayerStub
from gym.common.protobuf.gym_pb2 import Info, Layout

from gym.common.vnfbd import VNFBD
from gym.common.vnfpp import VNFPP


logger = logging.getLogger(__name__)


TESTS = {
    0: {"inputs": None, "template": None, "vnfbd": "vnf-bd-000.json",},
    1: {"inputs": None, "template": None, "vnfbd": "vnf-bd-001.json",},
    2: {"inputs": None, "template": None, "vnfbd": "vnf-bd-002.json",},
    3: {
        "inputs": "inputs-vnf-bd-003.json",
        "template": "template-vnf-bd-003.json",
        "vnfbd": "vnf-bd-003.json",
    },
    4: {
        "inputs": "inputs-vnf-bd-004.json",
        "template": "template-vnf-bd-004.json",
        "vnfbd": "vnf-bd-004.json",
    },
}


class Examples:
    def __init__(self):
        self.cfg = None
        self.info = {}

    def parse(self, argv=None):
        logger.info(f"parsing argv: {argv}")
        parser = argparse.ArgumentParser(description="Gym Examples App")

        parser.add_argument("--test", type=int, help="Define the test id (default: 0)")
        self.cfg, _ = parser.parse_known_args(argv)

        logger.info(f"args parsed: {self.cfg}")

        if self.cfg.test is not None:
            tests_ids = list(TESTS.keys())

            test_id = int(self.cfg.test)
            if test_id in tests_ids:
                self.info = TESTS.get(self.cfg.test)
                logger.info(f"Calling: example {self.cfg.test}")
                logger.info(f"{self.info}")
                return True
            else:
                logger.info(
                    f"Requested test id {test_id} not in available test set {tests_ids}"
                )

        return False

    async def callInfo(self, stub):
        info = Info()
        reply = await stub.Greet(info)
        reply_dict = json_format.MessageToDict(reply)
        logger.info(f"Received Info: {reply_dict}")

    def filepath(self, name):
        filepath = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "./source/", name)
        )
        return filepath

    def load(self, filename):
        try:
            with open(filename, "+r") as fp:
                data = json.load(fp)

        except Exception as e:
            logger.debug(f"Loading file exception: {e}")
            data = {}
        finally:
            return data

    def serialize_bytes(self, msg):
        msg_bytes = b""

        if type(msg) is dict:
            msg_str = json.dumps(msg)
            msg_bytes = msg_str.encode("utf32")

        return msg_bytes

    async def callLayout(self, stub):

        vnfbd_name = self.info.get("vnfbd")
        inputs_name = self.info.get("inputs")
        template_name = self.info.get("template")

        inputs_msg = bytes()
        template_msg = bytes()

        if inputs_name:
            inputs_filename = self.filepath(inputs_name)
            inputs = self.load(inputs_filename)
            inputs_msg = self.serialize_bytes(inputs)

        if template_name:
            template_filename = self.filepath(template_name)
            template = self.load(template_filename)
            template_msg = self.serialize_bytes(template)

        layout = Layout(id=self.cfg.test, inputs=inputs_msg, template=template_msg)

        vnfbd_filename = self.filepath(vnfbd_name)
        vnfbd = VNFBD()
        vnfbd.load(vnfbd_filename)
        vnfbd_protobuf = vnfbd.protobuf()
        layout.vnfbd.CopyFrom(vnfbd_protobuf)

        reply = await stub.CallLayout(layout)

        logger.info(f"Received Result {reply}")

        vnfpp = VNFPP()
        # ack = vnfpp.from_protobuf(reply.vnfpp)

        # if ack:
        #     logger.info(f"VNF-PP replied {vnfpp.json()}")

    async def calls(self):
        logger.info(f"Calling: info and layout")
        channel = Channel("172.17.0.1", 8990)
        stub = PlayerStub(channel)
        await self.callInfo(stub)
        await self.callLayout(stub)
        channel.close()

    async def run(self, argv):
        ack = self.parse(argv)
        if ack:
            await self.calls()
            return 0
        else:
            return -1


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    argv = sys.argv[1:]
    examples = Examples()
    asyncio.run(examples.run(argv))
