import logging
import asyncio
import json

from google.protobuf import json_format

from gym.common.protobuf.gym_grpc import InfraBase
from gym.common.protobuf.gym_pb2 import Deploy, Built

from gym.infra.containernet.plugin import ContainernetPlugin
from gym.infra.ssh.plugin import SSHPlugin

logger = logging.getLogger(__name__)


class Infra(InfraBase):
    def __init__(self, info):
        logger.info(f"Infra starting - uuid {info.get('uuid')}")
        self.plugins = {}
        self.plugin_instances = {}
        self.info = info
        self.load()

    def load(self):
        plugins = {
            "containernet": ContainernetPlugin,
            "ssh": SSHPlugin,
        }
        self.plugins = plugins

    async def play(self, command, environment, scenario):
        ack, info = False, {}

        orchestrator = environment.get("orchestrator")
        orchestrator_type = orchestrator.get("type")

        if orchestrator_type in self.plugins:
            plugin_instance = self.plugin_instances.get(orchestrator_type, None)

            if not plugin_instance:
                plugin_cls = self.plugins.get(orchestrator_type)
                plugin_instance = plugin_cls()
                self.plugin_instances[orchestrator_type] = plugin_instance

            if plugin_instance:
                if command == "start":
                    ack, info = await plugin_instance.start(scenario)
                elif command == "stop":
                    ack, info = await plugin_instance.stop(scenario)
                elif command == "update":
                    ack, info = await plugin_instance.update(scenario)
                else:
                    logger.info(f"Unknown infra plugin command {command}")

        else:
            logger.info(f"Unknown infra plugin {orchestrator_type}")

        return ack, info

    async def Run(self, stream):
        deploy = await stream.recv_message()
        deploy_dict = json_format.MessageToDict(
            deploy, preserving_proto_field_name=True
        )

        id_ = deploy_dict.get("id")
        command = deploy_dict.get("workflow")
        scenario = deploy_dict.get("scenario")
        environment = deploy_dict.get("environment")

        ok, info = await self.play(command, environment, scenario)
        info_json = json.dumps(info)
        built_info = info_json.encode("utf-8")
        built = Built(id=id_, ack=ok, info=built_info)

        await stream.send_message(built)
