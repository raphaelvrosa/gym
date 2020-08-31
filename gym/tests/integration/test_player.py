import os
import json
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
            command = "gym-{role} --uuid {uuid} --address {address} --contacts agent/127.0.0.1:50053 monitor/127.0.0.1:50054  &"
        else:
            command = "gym-{role} --uuid {uuid} --address {address} &"

        cmd_formatted = command.format(role=role, uuid=uuid, address=address)
        cmd_args = cmd_formatted.split(" ")
        p = start_process(cmd_args)
        return p

    def stop_component(self, p):
        ack = stop_process(p)
        return ack

    async def start_components(self, roles):
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
            await asyncio.sleep(2.0)

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
        request.role = "user"
        request.address = "0.0.0.0:50061"
        contacts = ["manager/127.0.0.1:50052"]
        for contact in contacts:
            request.contacts.append(contact)

        reply = await stub.Greet(request)
        reply_dict = json_format.MessageToDict(reply)

        return reply_dict

    async def run_info(self):
        roles = ["player", "manager", "agent", "monitor"]

        ps = await self.start_components(roles)

        await asyncio.sleep(2.0)

        channel = Channel("127.0.0.1", 50051)
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

    def filepath(self, name):
        filepath = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "./fixtures/", name)
        )
        return filepath

    def load(self, filename):
        try:
            with open(filename, "+r") as fp:
                data = json.load(fp)

        except Exception:
            data = {}
        finally:
            return data

    def serialize_bytes(self, msg):
        msg_bytes = b""

        if type(msg) is dict:
            msg_str = json.dumps(msg)
            msg_bytes = msg_str.encode("utf32")

        return msg_bytes

    async def call_layout(self, stub):
        _ = await self.call_info(stub)

        vnfbd_name = "vnf-bd-000.json"
        inputs_name = "inputs-vnf-bd-000.json"
        template_name = "template-vnf-bd-000.json"

        inputs_msg = bytes()
        template_msg = bytes()

        if inputs_name:
            inputs_filename = self.filepath(inputs_name)
            inputs = self.load(inputs_filename)
            inputs_msg = self.serialize_bytes(inputs)

        if template_name:
            template_filename = self.filepath(template_name)
            template = self.load(template_filename)
            template_msg = self.serialize_bytes(template)

        layout = gym_pb2.Layout(id=1, inputs=inputs_msg, template=template_msg)

        vnfbd_filename = self.filepath(vnfbd_name)
        vnfbd = VNFBD()
        vnfbd.load(vnfbd_filename)
        vnfbd_protobuf = vnfbd.protobuf()
        layout.vnfbd.CopyFrom(vnfbd_protobuf)
        reply = await stub.CallLayout(layout)
        reply_dict = json_format.MessageToDict(reply)

        return reply_dict

    async def run_layout(self):
        roles = ["player", "manager", "agent", "monitor"]

        ps = await self.start_components(roles)

        await asyncio.sleep(2.0)

        try:
            channel = Channel("127.0.0.1", 50051)
            stub = gym_grpc.PlayerStub(channel)
            result_reply = await self.call_layout(stub)
        except Exception as e:
            print(f"Exception calling layout {e}")

        finally:
            channel.close()

        await asyncio.sleep(2.0)

        ack = self.stop_components(ps)
        assert ack == True

        return result_reply

    def test_layout(self):
        result_reply = asyncio.run(self.run_layout())

        # import json

        # print(json.dumps(result_reply, indent=4))


if __name__ == "__main__":
    unittest.main()

    # t = TestPlayer()
    # t.test_layout()
