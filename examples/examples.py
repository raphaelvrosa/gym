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

from gym.common.yang.vnfbd import VNFBD
from gym.common.yang.vnfpp import VNFPP


logger = logging.getLogger(__name__)


TESTS = {
    0: {
        "inputs": "inputs-vnf-bd-000.json",
        "vnfbd": "vnf-bd-000.json",
    },
    1: {
        "inputs": "inputs-vnf-bd-001.json",
        "vnfbd": "vnf-bd-001.json",
    },
    2: {
        "inputs": "inputs-vnf-bd-002.json",
        "vnfbd": "vnf-bd-002.json",
    },
    3: {
        "inputs": "inputs-vnf-bd-003.json",
        "vnfbd": "vnf-bd-003.json",
    },
}


class Examples:
    def __init__(self):
        self.cfg = None
        self.info = {}

    def parse(self, argv=None):
        logger.info(f"parsing argv: {argv}")
        parser = argparse.ArgumentParser(
            description='Gym Examples App')

        parser.add_argument('--test',
                            type=int,
                            help='Define the test id (default: 0)')
        self.cfg, _ = parser.parse_known_args(argv)
        
        logger.info(f"args parsed: {self.cfg}")

        if self.cfg.test is not None:
            tests_ids = list(TESTS.keys())
            
            test_id = int(self.cfg.test)
            if test_id in tests_ids:
                self.info = TESTS.get(self.cfg.test)
                return True   
            else:
                logger.info(f"Requested test id {test_id} not in available test set {tests_ids}")

        return False

    async def callInfo(self, stub):
        info = Info()
        reply = await stub.Greet(info)
        reply_dict = json_format.MessageToDict(reply)
        logger.info(f"Received Info: {reply_dict}")

    def filepath(self, name):
        filepath = os.path.normpath(os.path.join(
            os.path.dirname(__file__),
            "./source/",
            name)
        )
        return filepath

    def load(self, filename):
        with open(filename, "+r") as fp:
            data = json.load(fp)
            return data

    async def callLayout(self, stub):
        layout = Layout(id=self.cfg.test)

        vnfbd_name = self.info.get("vnfbd")
        inputs_name = self.info.get("inputs")

        vnfbd_filename = self.filepath(vnfbd_name)
        inputs_filename = self.filepath(inputs_name)
        inputs = self.load(inputs_filename)

        vnfbd = VNFBD()
        vnfbd.load(vnfbd_filename, yang=False)
        vnfbd_protobuf = vnfbd.protobuf()

        logger.info(f"vnf-bd protobuf: {vnfbd_protobuf}")

        layout.vnfbd.CopyFrom(vnfbd_protobuf)
        for k,v in inputs.items():
            layout.inputs[k] = v

        reply = await stub.CallLayout(layout)

        logger.info(f"Received Result {reply}")

        vnfpp = VNFPP()
        ack = vnfpp.from_protobuf(reply.vnfpp)

        if ack:
            
            logger.info(f"VNF-PP replied {vnfpp.json()}")
        
      
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