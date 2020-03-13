import logging

from gym.common.core import ManagerCore
from gym.common.protobuf.gym_grpc import ManagerBase


logger = logging.getLogger(__name__)


class Manager(ManagerBase):
    
    def __init__(self, info):
        self.core = ManagerCore(info)

    async def Greet(self, stream):
        request = await stream.recv_message()
        reply = await self.core.info(request)
        await stream.send_message(reply)

    async def CallTask(self, stream):
        request = await stream.recv_message()
        reply = await self.core.task(request)
        await stream.send_message(reply)