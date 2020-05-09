import unittest
import asyncio
from grpclib.client import Channel
from google.protobuf import json_format

from gym.common.protobuf import gym_pb2
from gym.common.protobuf import gym_grpc


from utils import start_process, stop_process


class TestAgent(unittest.TestCase):

    def start_agent(self, uuid, address):
        command = "gym-agent --uuid {uuid} --address {address} --debug &"
        cmd_formatted = command.format(uuid=uuid, address=address)
        cmd_args = cmd_formatted.split(" ")
        p = start_process(cmd_args)
        return p

    def stop_agent(self, agent_process):
        ack = stop_process(agent_process)
        return ack

    async def call_info(self, stub):
        request = gym_pb2.Info()
        request.uuid = '0'
        request.role = 'manager'
        request.address = "0.0.0.0:50061"
            
        reply = await stub.Greet(request)
        reply_dict = json_format.MessageToDict(reply)

        return reply_dict

    async def run_info(self):
        uuid, address = "agent-test", "127.0.0.1:50051"

        p = self.start_agent(uuid, address)

        await asyncio.sleep(1.0)
        channel =  Channel('127.0.0.1', 50051)
        stub = gym_grpc.AgentStub(channel)
        info_reply = await self.call_info(stub)
        channel.close()

        ack = self.stop_agent(p)
        assert ack == True

        return info_reply

    async def call_instruction(self, stub):
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

        reply_dict = json_format.MessageToDict(reply)

        return reply_dict

    async def run_instruction(self):
        uuid, address = "agent-test", "127.0.0.1:50051"
        p = self.start_agent(uuid, address)

        await asyncio.sleep(1.0)
        channel =  Channel('127.0.0.1', 50051)
        stub = gym_grpc.AgentStub(channel)
        instruction_reply = await self.call_instruction(stub)
        channel.close()

        ack = self.stop_agent(p)
        assert ack == True

        return instruction_reply

    def test_info(self):
        info_reply = asyncio.run(self.run_info())

        assert info_reply.get("role") == "agent"
        assert info_reply.get("address") == "127.0.0.1:50051"

        probers = info_reply.get("artifacts").get("probers")
        ping_prober_ls = [p for p in probers if p.get("id") == 2]
        ping_prober = ping_prober_ls.pop()

        assert ping_prober.get("name") == "ping"


    def test_instruction(self):
        instruction_reply = asyncio.run(self.run_instruction())

        



if __name__ == "__main__":
    unittest.main()