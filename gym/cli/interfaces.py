import sys
import json
import asyncio
import logging
from datetime import datetime
from google.protobuf import json_format
from grpclib.client import Channel
from grpclib.exceptions import GRPCError

from gym.common.protobuf.gym_grpc import PlayerStub
from gym.common.protobuf.gym_pb2 import Info, Layout


logger = logging.getLogger(__name__)


class GymInterface:
    def __init__(self):
        pass

    def parse_bytes(self, msg):
        msg_dict = {}

        if type(msg) is bytes:
            msg_str = msg.decode("utf-8")
            msg_dict = json.loads(msg_str)

        return msg_dict

    def serialize_bytes(self, msg):
        msg_bytes = b""

        if type(msg) is dict:
            msg_str = json.dumps(msg)
            msg_bytes = msg_str.encode("utf-8")

        return msg_bytes

    async def call_stub(self, stub_func, msg):
        reply, error = {}, ""
        try:
            msg_reply = await stub_func(msg)

            reply = json_format.MessageToDict(
                msg_reply, preserving_proto_field_name=True
            )

        except GRPCError as e:
            error = f"Could not reach stub grpcerror - exception {repr(e)} "
            logger.debug(f"Exception: {error}")

        except OSError as e:
            error = f"Could not reach stub channel - exception {repr(e)} "
            logger.debug(f"Exception: {error}")

        finally:
            return reply, error


class GymPlayerInterface(GymInterface):
    def __init__(self):
        GymInterface.__init__(self)

    async def call(self, operation, address, vnfbr):
        vnfbr_pb = vnfbr.protobuf()
        layout = Layout(feat=operation)
        layout.vnfbr.CopyFrom(vnfbr_pb)

        ip, port = address.split(":")
        channel = Channel(ip, port)
        stub = PlayerStub(channel)

        reply, error = await self.call_stub(stub.CallLayout, layout)

        channel.close()
        return reply, error
