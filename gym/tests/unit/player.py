import os
import yaml
import json
import logging
import asyncio
from grpclib.client import Channel

from google.protobuf import json_format

from gym.common.protobuf import gym_grpc
from gym.common.protobuf import gym_pb2

from gym.common.yang.vnfbd import VNFBD



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

async def test_scenario():
    filename = filepath('vnf-bd-001.json')
    vnfbd = VNFBD()
    vnfbd.load(filename)

    ack = await callScenario("start", 1, vnfbd)
    
    await asyncio.sleep(5)

    ack = await callScenario("stop", 1, vnfbd)


async def callInfo(stub):
    info = gym_pb2.Info()
    reply = await stub.Greet(info)
    print(reply)

def filepath(name):
    filepath = os.path.normpath(os.path.join(
        os.path.dirname(__file__),
        "./db/vnf-bds/",
        name)
    )
    return filepath

async def callLayout(stub):
    pass

def load(filename):
    try:
        with open(filename, "+r") as fp:
            data = json.load(fp)
            
    except Exception as e:
        logger.debug(f"Loading file exception: {e}")
        data = {}
    finally:
        return data


def test_vnfbd():
    vfilename = filepath('vnf-bd-003.json')
    ifilename = filepath('inputs-vnf-bd-003.json')
    tfilename = filepath('template-vnf-bd-003.json')

    template = load(tfilename)
    inputs = load(ifilename)



    vnfbd = VNFBD()
    vnfbd.load(vfilename)

    vnfbd.inputs(inputs)
    
    templates = vnfbd.multiplex(template)

    print(len(templates))


async def main():
    channel = Channel("172.17.0.1", 8990)
    stub = gym_grpc.PlayerStub(channel)
    await callInfo(stub)
    # await callLayout(stub)
    channel.close()

    # test_vnfbd()
    # await test_scenario()
    

if __name__ == "__main__":
    
    logging.basicConfig(level=logging.DEBUG)
    # asyncio.run(main())

    test_vnfbd()