import unittest
import asyncio
from grpclib.client import Channel
from google.protobuf import json_format

from gym.common.protobuf import gym_pb2
from gym.common.protobuf import gym_grpc

from utils import start_process, stop_process

from gym.common.vnfbd import VNFBD


class TestPlayer(unittest.TestCase):



    def start_component(self, role, uuid, address):

        if role == "manager":
            command = "gym-{role} --uuid {uuid} --address {address} --contacts agent/127.0.0.1:50053 monitor/127.0.0.1:50054 --debug &"
        else:
            command = "gym-{role} --uuid {uuid} --address {address} --debug &"
        
        cmd_formatted = command.format(role=role, uuid=uuid, address=address)
        cmd_args = cmd_formatted.split(" ")
        p = start_process(cmd_args)
        return p

    def stop_component(self, p):
        ack = stop_process(p)
        return ack

    def start_components(self, roles):
        processes = []
        t = 1
        for role in roles:
            uuid, address = "{role}-test".format(role=role), "127.0.0.1:5005{t}".format(t=str(t))
            p = self.start_component(role, uuid, address)
            processes.append(p)
            t += 1
        
        return processes

    def stop_components(self, processes):
        acks = []
        for p in processes:
            ack = self.stop_component(p)
            acks.append(ack)

        return all(acks)


    async def call_info(self, stub):
        request = gym_pb2.Info()
        request.uuid = '0'
        request.role = 'user'
        request.address = "0.0.0.0:50061"
        contacts = ["manager/127.0.0.1:50052"]
        for contact in contacts:
            request.contacts.append(contact)
            
        reply = await stub.Greet(request)
        reply_dict = json_format.MessageToDict(reply)

        return reply_dict

    async def run_info(self):
        roles = ["player", "manager", "agent", "monitor"]

        ps = self.start_components(roles)

        await asyncio.sleep(2.0)

        channel =  Channel('127.0.0.1', 50051)
        stub = gym_grpc.PlayerStub(channel)
        info_reply = await self.call_info(stub)
        channel.close()

        ack = self.stop_components(ps)
        assert ack == True

        return info_reply

    def test_info(self):

        info_reply = asyncio.run(self.run_info())

        assert info_reply.get("role") == "player"
        assert info_reply.get("address") == "127.0.0.1:50051"


    # def test_vnfbd(self):
    #     pass


if __name__ == "__main__":
    unittest.main()