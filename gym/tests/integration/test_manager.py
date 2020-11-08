import logging
import unittest
import asyncio
import json

from grpclib.client import Channel
from google.protobuf import json_format

from gym.common.protobuf import gym_pb2
from gym.common.protobuf import gym_grpc


from utils import start_process, stop_process


logger = logging.getLogger(__name__)


class TestManager(unittest.TestCase):
    def start_component(self, role, uuid, address):
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
            uuid, address = (
                "{role}-test".format(role=role),
                "127.0.0.1:5005{t}".format(t=str(t)),
            )
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
        request.uuid = "0"
        request.role = "player"
        request.address = "0.0.0.0:50061"
        contacts = ["agent/127.0.0.1:50051", "monitor/127.0.0.1:50052"]
        for contact in contacts:
            request.contacts.append(contact)

        reply = await stub.Greet(request)
        reply_dict = json_format.MessageToDict(reply)

        return reply_dict

    async def run_info(self):
        roles = ["agent", "monitor", "manager"]

        ps = self.start_components(roles)

        await asyncio.sleep(2.0)

        channel = Channel("127.0.0.1", 50053)
        stub = gym_grpc.ManagerStub(channel)
        info_reply = await self.call_info(stub)
        channel.close()

        ack = self.stop_components(ps)
        assert ack == True

        return info_reply

    async def call_task(self, stub):

        info_reply = await self.call_info(stub)

        request = gym_pb2.Task(id=10, test=1, trials=1)
        # agent = request.agents.add()
        # agent.uuid = "agent-test"
        # prober = agent.probers.add()
        # prober.id = 2
        # prober.parameters["target"] = "1.1.1.1"
        # prober.parameters["packets"] = "3"

        # monitor = request.monitors.add()
        # monitor.uuid = "monitor-test"
        # listener = monitor.listeners.add()
        # listener.id = 10
        # listener.parameters["interval"] = "1"
        # listener.parameters["duration"] = "3"

        task_template = {
            "agents": [
                {
                    "uuid": "agent-test",
                    "probers": [
                        {
                            "id": 2,
                            "name": "ping",
                            "parameters": {"target": "1.1.1.1", "packets": "3"},
                        }
                    ],
                }
            ],
            "monitors": [
                {
                    "uuid": "monitor-test",
                    "listeners": [
                        {
                            "id": 10,
                            "name": "host",
                            "parameters": {"duration": "3", "interval": "1"},
                        }
                    ],
                }
            ],
        }

        request = json_format.ParseDict(task_template, request)

        reply = await stub.CallTask(request)

        reply_dict = json_format.MessageToDict(reply)

        return reply_dict

    async def run_task(self):
        roles = ["agent", "monitor", "manager"]

        ps = self.start_components(roles)

        await asyncio.sleep(3.0)

        channel = Channel("127.0.0.1", 50053)
        stub = gym_grpc.ManagerStub(channel)
        task_reply = await self.call_task(stub)

        channel.close()

        ack = self.stop_components(ps)
        assert ack == True

        return task_reply

    def test_info(self):
        info_reply = asyncio.run(self.run_info())

        assert info_reply.get("role") == "manager"
        assert info_reply.get("address") == "127.0.0.1:50053"

        agents = info_reply.get("apparatus").get("agents")
        agent = agents[0]
        probers = agent.get("artifacts").get("probers")
        ping_prober_ls = [p for p in probers if p.get("id") == 2]
        ping_prober = ping_prober_ls.pop()

        assert ping_prober.get("name") == "ping"

        monitors = info_reply.get("apparatus").get("monitors")
        monitor = monitors[0]
        listeners = monitor.get("artifacts").get("listeners")
        host_listener_ls = [p for p in listeners if p.get("id") == 10]
        host_listener = host_listener_ls.pop()

        assert host_listener.get("name") == "host"

    def test_task(self):

        # {
        # 'test': 1,
        # 'snapshots': {
        # 1001: {'id': 1001, 'origin': {'id': 'agent-test', 'role': 'agent'}, 'evaluations': [{'id': 1, 'metrics': {'rtt_min': {'name': 'rtt_min', 'type': 'float', 'unit': 'ms', 'scalar': 151.996}, 'rtt_avg': {'name': 'rtt_avg', 'type': 'float', 'unit': 'ms', 'scalar': 158.256}, 'rtt_max': {'name': 'rtt_max', 'type': 'float', 'unit': 'ms', 'scalar': 162.686}, 'rtt_mdev': {'name': 'rtt_mdev', 'type': 'float', 'unit': 'ms', 'scalar': 4.551}, 'frame_loss': {'name': 'frame_loss', 'type': 'float', 'unit': '%', 'scalar': 0.0}}}], 'timestamp': '2020-05-10T16:10:45.235735Z'},
        # 1002: {'id': 1002, 'origin': {'id': 'monitor-test', 'role': 'monitor'}, 'evaluations': [{'id': 1, 'metrics': {'cpu_percent': {'name': 'cpu_percent', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 20.5}, '1': {'key': 1.0, 'value': 8.0}}}, 'user_time': {'name': 'user_time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 215886.05}, '1': {'key': 1.0, 'value': 215887.38}}}, 'nice_time': {'name': 'nice_time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 410.26}, '1': {'key': 1.0, 'value': 410.26}}}, 'system_time': {'name': 'system_time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 40699.0}, '1': {'key': 1.0, 'value': 40699.2}}}, 'idle_time': {'name': 'idle_time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 511926.72}, '1': {'key': 1.0, 'value': 511943.2}}}, 'iowait_time': {'name': 'iowait_time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 164.76}, '1': {'key': 1.0, 'value': 164.76}}}, 'irq_time': {'name': 'irq_time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 0.0}, '1': {'key': 1.0, 'value': 0.0}}}, 'softirq_time': {'name': 'softirq_time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 25077.05}, '1': {'key': 1.0, 'value': 25077.16}}}, 'steal_time': {'name': 'steal_time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 0.0}, '1': {'key': 1.0, 'value': 0.0}}}, 'guest_time': {'name': 'guest_time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 2683.42}, '1': {'key': 1.0, 'value': 2683.42}}}, 'guest_nice_time': {'name': 'guest_nice_time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 0.0}, '1': {'key': 1.0, 'value': 0.0}}}, 'mem_percent': {'name': 'mem_percent', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 36.4}, '1': {'key': 1.0, 'value': 36.3}}}, 'total_mem': {'name': 'total_mem', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 15719.4453125}, '1': {'key': 1.0, 'value': 15719.4453125}}}, 'available_mem': {'name': 'available_mem', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 10001.55078125}, '1': {'key': 1.0, 'value': 10011.14453125}}}, 'used_mem': {'name': 'used_mem', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 4390.91015625}, '1': {'key': 1.0, 'value': 4390.3828125}}}, 'free_mem': {'name': 'free_mem', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 2143.4765625}, '1': {'key': 1.0, 'value': 2152.76953125}}}, 'active_mem': {'name': 'active_mem', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 6367.9453125}, '1': {'key': 1.0, 'value': 6367.7890625}}}, 'inactive_mem': {'name': 'inactive_mem', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 5968.55859375}, '1': {'key': 1.0, 'value': 5960.17578125}}}, 'buffers_mem': {'name': 'buffers_mem', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 309.42578125}, '1': {'key': 1.0, 'value': 309.42578125}}}, 'cached_mem': {'name': 'cached_mem', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 8875.6328125}, '1': {'key': 1.0, 'value': 8866.8671875}}}, 'shared_mem': {'name': 'shared_mem', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 1037.58203125}, '1': {'key': 1.0, 'value': 1028.89453125}}}, 'slab_mem': {'name': 'slab_mem', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 578.99609375}, '1': {'key': 1.0, 'value': 578.99609375}}}, 'read_count': {'name': 'read_count', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 420070.0}, '1': {'key': 1.0, 'value': 420070.0}}}, 'read_bytes': {'name': 'read_bytes', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 22622246912.0}, '1': {'key': 1.0, 'value': 22622246912.0}}}, 'write_count': {'name': 'write_count', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 3432325.0}, '1': {'key': 1.0, 'value': 3432325.0}}}, 'write_bytes': {'name': 'write_bytes', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 109042034688.0}, '1': {'key': 1.0, 'value': 109042034688.0}}}, 'time': {'name': 'time', 'type': 'float', 'series': {'0': {'key': 0.0, 'value': 1589137843.072228}, '1': {'key': 1.0, 'value': 1589137844.5775416}}}}}], 'timestamp': '2020-05-10T16:10:46.108810Z'}}, 'timestamp': '2020-05-10T16:10:46.163916Z'}

        task_reply = asyncio.run(self.run_task())

        snaps = task_reply.get("snapshots")

        assert type(snaps) is dict

        snap1 = snaps.get(1001)
        snap2 = snaps.get(1002)

        snap1_origin = snap1.get("origin").get("id")
        snap2_origin = snap2.get("origin").get("id")
        origins = [snap1_origin, snap2_origin]

        expected_origins = ["agent-test", "monitor-test"]
        origins_ok = [True if o in expected_origins else False for o in origins]

        assert all(origins_ok) == True

        logger.debug(json.dumps(task_reply, indent=4, sort_keys=True))


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(threadName)s %(name)s %(message)s",
    )
    unittest.main()
    # t = TestManager()
    # t.test_task()
