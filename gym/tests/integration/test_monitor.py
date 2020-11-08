import unittest
import asyncio
from grpclib.client import Channel
from google.protobuf import json_format

from gym.common.protobuf import gym_pb2
from gym.common.protobuf import gym_grpc


from utils import start_process, stop_process


class Testmonitor(unittest.TestCase):
    def start_monitor(self, uuid, address):
        command = "gym-monitor --uuid {uuid} --address {address} --debug &"
        cmd_formatted = command.format(uuid=uuid, address=address)
        cmd_args = cmd_formatted.split(" ")
        p = start_process(cmd_args)
        return p

    def stop_monitor(self, monitor_process):
        ack = stop_process(monitor_process)
        return ack

    async def call_info(self, stub):
        request = gym_pb2.Info()
        request.uuid = "0"
        request.role = "manager"
        request.address = "0.0.0.0:50061"

        reply = await stub.Greet(request)
        reply_dict = json_format.MessageToDict(reply)

        return reply_dict

    async def run_info(self):
        uuid, address = "monitor-test", "127.0.0.1:50051"

        p = self.start_monitor(uuid, address)

        await asyncio.sleep(1.0)
        channel = Channel("127.0.0.1", 50051)
        stub = gym_grpc.MonitorStub(channel)
        info_reply = await self.call_info(stub)
        channel.close()

        ack = self.stop_monitor(p)
        assert ack == True

        return info_reply

    async def call_instruction(self, stub):
        request = gym_pb2.Instruction()
        request.id = 1
        request.trial = 1

        action = request.actions.add()
        action.name = "host"
        action.id = 10
        action.args["duration"] = "3"
        action.args["interval"] = "1"

        action = request.actions.add()
        action.name = "process"
        action.id = 12
        action.args["pid"] = "1"
        action.args["duration"] = "3"
        action.args["interval"] = "1"

        reply = await stub.CallInstruction(request)

        reply_dict = json_format.MessageToDict(reply)

        return reply_dict

    async def run_instruction(self):
        uuid, address = "monitor-test", "127.0.0.1:50051"
        p = self.start_monitor(uuid, address)

        await asyncio.sleep(1.0)
        channel = Channel("127.0.0.1", 50051)
        stub = gym_grpc.MonitorStub(channel)
        instruction_reply = await self.call_instruction(stub)
        channel.close()

        ack = self.stop_monitor(p)
        assert ack == True

        return instruction_reply

    def test_info(self):
        info_reply = asyncio.run(self.run_info())

        assert info_reply.get("role") == "monitor"
        assert info_reply.get("address") == "127.0.0.1:50051"

        listeners = info_reply.get("artifacts").get("listeners")
        host_listener_ls = [p for p in listeners if p.get("id") == 10]
        host_listener = host_listener_ls.pop()

        assert host_listener.get("name") == "host"

    def test_instruction(self):

        instruction_reply = asyncio.run(self.run_instruction())

        origin = instruction_reply.get("origin")
        assert origin.get("id") == "monitor-test"
        assert origin.get("role") == "monitor"

        evals = instruction_reply.get("evaluations")

        import json

        print(json.dumps(instruction_reply, indent=4))

        assert type(evals) is dict


if __name__ == "__main__":
    unittest.main()
    # t = Testmonitor()
    # t.test_instruction()
