import logging

from gym.common.core import PlayerCore
from gym.common.protobuf.gym_grpc import PlayerBase

from gym.common.tools import Loader

logger = logging.getLogger(__name__)


class Player(PlayerBase):
    def __init__(self, info):
        logger.info(f"Player starting - uuid {info.get('uuid')}")
        self.core = PlayerCore(info)

    async def Greet(self, stream):
        request = await stream.recv_message()
        reply = await self.core.info(request)
        await stream.send_message(reply)

    async def CallLayout(self, stream):
        request = await stream.recv_message()
        reply = await self.core.layout(request)
        await stream.send_message(reply)

