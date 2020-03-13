import os
import asyncio
import logging
from datetime import datetime

from gym.common.core import WorkerCore
from gym.common.protobuf.gym_grpc import MonitorBase
from gym.common.protobuf.gym_pb2 import Instruction, Snapshot, Evaluation, Info, Environment


logger = logging.getLogger(__name__)


class Monitor(MonitorBase):

    def __init__(self, info):
        asyncio.create_task(self.load())
        self.core = WorkerCore(info)

    async def load(self):
        folder = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            'listeners'
        )
        await self.core.load(folder, "listeners")

    async def Greet(self, stream):
        request: Info = await stream.recv_message()
        reply = await self.core.info(request)
        await stream.send_message(reply)

    async def CallInstruction(self, stream):
        request: Instruction = await stream.recv_message()       
        reply = await self.core.instruction(request)
        await stream.send_message(reply)

