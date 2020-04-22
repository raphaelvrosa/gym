import os
import asyncio
import logging

from gym.common.core import WorkerCore
from gym.common.protobuf.gym_grpc import AgentBase
from gym.common.protobuf.gym_pb2 import Instruction, Info


logger = logging.getLogger(__name__)


class Agent(AgentBase):
    def __init__(self, info):
        logger.info(f"Agent starting - uuid {info.get('uuid')}")
        info['folder'] = self._folder()
        self.core = WorkerCore(info)

    def _folder(self):
        folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'probers'
        )
        return folder

    async def Greet(self, stream):
        request: Info = await stream.recv_message()
        reply = await self.core.info(request)
        await stream.send_message(reply)

    async def CallInstruction(self, stream):
        request: Instruction = await stream.recv_message()       
        reply = await self.core.instruction(request)
        await stream.send_message(reply)

