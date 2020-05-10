import logging
import os
from gym.infra.ssh.plugin import SSHProxy

logging.basicConfig(level=logging.DEBUG)

proxy = SSHProxy()

cfg = {
    "address": {
        "value": "172.17.0.2",
    },
    "port": {
        "value": "22",
    },
    "user": {
        "value": "gym",
    },
    "password": {
        "value": "R0cks.4l1v3",
    },
}

proxy.cfg(cfg)

filepath = os.path.join(
    os.path.dirname(__file__), 
    "gym.tar.xz")

proxy.upload_file(filepath, "/home/gym/")

cmd =   "cd /home/gym/ && tar xf gym.tar.xz && "\
        "cd gym && sudo python3.7 setup.py install"

ack = proxy.execute_command(cmd)
print(f"command ack {ack}")

cmd = "gym-agent --uuid agent --address 172.17.0.2:50056 > gym-agent.log 2>&1 &"
ack = proxy.execute_command(cmd)
print(f"command ack {ack}")



import unittest
import os
import yaml
import json
import asyncio
from grpclib.client import Channel

from google.protobuf import json_format

from gym.common.protobuf import gym_grpc
from gym.common.protobuf import gym_pb2

from gym.common.vnfbd import VNFBD


async def callScenario(command, test, vnfbd):
    deploy_dict = {
        "id": test,
        "workflow": command,
        "scenario": vnfbd.scenario(),
    }
    deploy = json_format.ParseDict(deploy_dict, gym_pb2.Deploy())
    
    environment = vnfbd.environment()
    env_plugin = environment.get("plugin")
    env_params = env_plugin.get("parameters")
    address = env_params.get("address").get("value")
    host, port = address.split(":")

    channel = Channel(host, port)
    stub = gym_grpc.InfraStub(channel)
    built = await stub.Run(deploy)

    if built.error:
        ack = False
        print(f'Scenario not deployed error: {built.error}')
    else:
        ack = True
        print(f'Scenario deployed: {built.ack}')


    channel.close()
    return ack

async def run_scenario():
    filename = filepath('vnf-bd-001.json')
    vnfbd = VNFBD()
    vnfbd.load(filename)

    ack = await callScenario("start", 1, vnfbd)
    
    await asyncio.sleep(5)

    ack = await callScenario("stop", 1, vnfbd)


def test_scenario():
    asyncio.run(run_scenario())
