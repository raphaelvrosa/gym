import logging

import asyncio

from grpclib.client import Channel


from gym.common.protobuf import gym_pb2
from gym.common.protobuf import gym_grpc

async def call_Info(stub):
    request = gym_pb2.Info()
    request.uuid = '2'
    request.role = 'manager'
    request.address = "0.0.0.0:50051"
        
    reply = await stub.Greet(request)
    print(reply)


async def call_Instruction(stub):
    request = gym_pb2.Instruction()
    request.id = 1    
    request.trial = 1
    
    action = request.actions.get_or_create(10)
    action.id = 2
    action.args['packets'] = '3'
    action.args['target'] = '1.1.1.1'
    
    
    action = request.actions.get_or_create(11)
    action.id = 2
    action.args['packets'] = '2'
    action.args['target'] = '8.8.8.8'
    
    
    reply = await stub.CallInstruction(request)
    print(reply)


async def init():
    channel =  Channel('localhost', 50052)
    stub = gym_grpc.AgentStub(channel)
    # await call_Info(stub)
    await call_Instruction(stub)
    channel.close()


if __name__ == "__main__":
    logging.basicConfig()
    asyncio.run(init())