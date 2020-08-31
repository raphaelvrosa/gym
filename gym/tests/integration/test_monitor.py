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

        action = request.actions.get_or_create(10)
        action.id = 10
        action.args["duration"] = "3"
        action.args["interval"] = "1"

        action = request.actions.get_or_create(11)
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

        # {'id': 1, 'trial': 1, 'origin': {'id': 'monitor-test', 'role': 'monitor'}, 'evaluations': [{'id': 10, 'metrics': {'cpu_percent': {'name': 'cpu_percent', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 0.7}, '1': {'key': 1.0, 'value': 0.8}}}, 'user_time': {'name': 'user_time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 214488.08}, '1': {'key': 1.0, 'value': 214488.26}}}, 'nice_time': {'name': 'nice_time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 405.41}, '1': {'key': 1.0, 'value': 405.41}}}, 'system_time': {'name': 'system_time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 40414.26}, '1': {'key': 1.0, 'value': 40414.3}}}, 'idle_time': {'name': 'idle_time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 480088.9}, '1': {'key': 1.0, 'value': 480106.75}}}, 'iowait_time': {'name': 'iowait_time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 156.31}, '1': {'key': 1.0, 'value': 156.32}}}, 'irq_time': {'name': 'irq_time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 0.0}, '1': {'key': 1.0, 'value': 0.0}}}, 'softirq_time': {'name': 'softirq_time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 24928.7}, '1': {'key': 1.0, 'value': 24928.72}}}, 'steal_time': {'name': 'steal_time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 0.0}, '1': {'key': 1.0, 'value': 0.0}}}, 'guest_time': {'name': 'guest_time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 2683.42}, '1': {'key': 1.0, 'value': 2683.42}}}, 'guest_nice_time': {'name': 'guest_nice_time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 0.0}, '1': {'key': 1.0, 'value': 0.0}}}, 'mem_percent': {'name': 'mem_percent', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 32.6}, '1': {'key': 1.0, 'value': 32.6}}}, 'total_mem': {'name': 'total_mem', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 15719.4453125}, '1': {'key': 1.0, 'value': 15719.4453125}}}, 'available_mem': {'name': 'available_mem', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 10588.27734375}, '1': {'key': 1.0, 'value': 10598.875}}}, 'used_mem': {'name': 'used_mem', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 3944.78125}, '1': {'key': 1.0, 'value': 3940.83984375}}}, 'free_mem': {'name': 'free_mem', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 2744.3203125}, '1': {'key': 1.0, 'value': 2754.91796875}}}, 'active_mem': {'name': 'active_mem', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 5909.5546875}, '1': {'key': 1.0, 'value': 5902.734375}}}, 'inactive_mem': {'name': 'inactive_mem', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 5873.39453125}, '1': {'key': 1.0, 'value': 5867.6796875}}}, 'buffers_mem': {'name': 'buffers_mem', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 301.95703125}, '1': {'key': 1.0, 'value': 301.95703125}}}, 'cached_mem': {'name': 'cached_mem', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 8728.38671875}, '1': {'key': 1.0, 'value': 8721.73046875}}}, 'shared_mem': {'name': 'shared_mem', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 899.28125}, '1': {'key': 1.0, 'value': 892.625}}}, 'slab_mem': {'name': 'slab_mem', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 575.203125}, '1': {'key': 1.0, 'value': 575.203125}}}, 'read_count': {'name': 'read_count', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 420003.0}, '1': {'key': 1.0, 'value': 420003.0}}}, 'read_bytes': {'name': 'read_bytes', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 22620698624.0}, '1': {'key': 1.0, 'value': 22620698624.0}}}, 'write_count': {'name': 'write_count', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 3416980.0}, '1': {'key': 1.0, 'value': 3416994.0}}}, 'write_bytes': {'name': 'write_bytes', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 108739655680.0}, '1': {'key': 1.0, 'value': 108739729408.0}}}, 'time': {'name': 'time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 1589135045.0152802}, '1': {'key': 1.0, 'value': 1589135046.5199692}}}}}], 'timestamp': '2020-05-10T15:24:08.036813Z'}

        instruction_reply = asyncio.run(self.run_instruction())

        origin = instruction_reply.get("origin")
        assert origin.get("id") == "monitor-test"
        assert origin.get("role") == "monitor"

        evals = instruction_reply.get("evaluations")

        # import json
        # print(json.dumps(instruction_reply, indent=4))

        assert type(evals) is list


if __name__ == "__main__":
    # unittest.main()

    t = Testmonitor()
    t.test_instruction()
