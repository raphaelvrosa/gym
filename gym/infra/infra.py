import logging
import asyncio
import json

from google.protobuf import json_format

from gym.common.protobuf.gym_grpc import InfraBase
from gym.common.protobuf.gym_pb2 import Deploy, Built

from gym.infra.containernet.plugin import ContainernetPlugin

logger = logging.getLogger(__name__)


class Infra(InfraBase):

    def __init__(self, info):
        self.plugins = {}
        self.plugin_instances = {}
        self.info = info
        self.load()

    def load(self):
        plugins = {
            "containernet": ContainernetPlugin,
        }
        self.plugin_instances = plugins

    async def play(self, command, environment, scenario):
        ack, info = False, {}

        plugin = environment.get("plugin")
        if plugin in self.plugins:
            plugin_instance = self.plugin_instances.get(plugin, None)

            if not plugin_instance:                    
                plugin_cls = self.plugins.get(plugin)
                plugin_instance = plugin_cls()
                self.plugin_instances[plugin] = plugin_instance
            
            if command == "start":
                ack, info = plugin_instance.start(scenario)
            elif command == "stop":
                ack, info = plugin_instance.stop(scenario)
            elif command == "update":
                ack, info = plugin_instance.update(scenario)
            else:
                logger.info(f"Unknown infra plugin command {command}")

        else:
            logger.info(f"Unknown infra plugin {plugin}")
        
        return ack, info                   

    async def Run(self, stream):
        deploy = await stream.recv_message()        
        deploy_dict = json_format.MessageToDict(deploy, preserving_proto_field_name=True)
        
        id = deploy_dict.get("id")
        command = deploy_dict.get("workflow")
        scenario = deploy_dict.get("scenario")
        environment = deploy_dict.get("environment")
        
        ok, msg = await self.play(command, environment, scenario)
        info = json.dumps(msg.get("info"))
        built_info = info.encode('utf-8')
        built = Built(id=id, ack=ok, info=built_info)
        
        await stream.send_message(built)

