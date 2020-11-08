import json
import unittest
import asyncio
from grpclib.client import Channel
from google.protobuf import json_format

from gym.common.protobuf import gym_pb2
from gym.common.protobuf import gym_grpc


async def call_instruction(stub):
    request = gym_pb2.Instruction()
    request.id = 1
    request.trial = 1

    action = request.actions.get_or_create(10)
    action.id = 2
    action.args["packets"] = "5"
    action.args["target"] = "1.1.1.1"

    # action = request.actions.get_or_create(11)
    # action.id = 2
    # action.args["packets"] = "2"
    # action.args["target"] = "8.8.8.8"

    reply = await stub.CallInstruction(request)

    reply_dict = json_format.MessageToDict(reply)

    return reply_dict


async def run_instruction(address, port):

    channel = Channel(address, port)
    stub = gym_grpc.AgentStub(channel)
    instruction_reply = await call_instruction(stub)
    channel.close()

    return instruction_reply


def instruction():
    address, port = "127.0.0.1", 9090

    instruction_reply = asyncio.run(run_instruction(address, port))

    print(json.dumps(instruction_reply, sort_keys=True, indent=4))


async def call_info(stub):
    request = gym_pb2.Info()
    request.uuid = "0"
    request.role = "manager"
    request.address = "0.0.0.0:50061"

    reply = await stub.Greet(request)
    reply_dict = json_format.MessageToDict(reply)

    return reply_dict


async def run_info(address, port):

    channel = Channel(address, port)
    stub = gym_grpc.AgentStub(channel)
    info_reply = await call_info(stub)
    channel.close()

    return info_reply


def info():
    address, port = "127.0.0.1", 9090
    instruction_reply = asyncio.run(run_info(address, port))
    print(json.dumps(instruction_reply, sort_keys=True, indent=4))


if __name__ == "__main__":
    info()
