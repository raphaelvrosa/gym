import logging

import asyncio

from grpclib.client import Channel


from gym.common.protobuf import gym_pb2
from gym.common.protobuf import gym_grpc

async def call_Info(stub):
    request = gym_pb2.Info()
    request.uuid = '50'
    request.role = 'player'
    request.address = "0.0.0.0:50050"
       
    reply = await stub.Greet(request)
    print(reply)


async def call_Task(stub):
    request = gym_pb2.Task(test=1, trials=1)
    agent = request.agents.add()
    agent.uuid = "1"
    prober = agent.probers.add()
    prober.id = 2
    prober.parameters["target"] = "1.1.1.1"
    prober.parameters["packets"] = "3"

    reply = await stub.CallTask(request)
    print(reply)

async def init():
    channel =  Channel('localhost', 50051)
    stub = gym_grpc.ManagerStub(channel)
    await call_Info(stub)
    await call_Task(stub)
    channel.close()


if __name__ == "__main__":
    logging.basicConfig()
    asyncio.run(init())