import json
import asyncio
import logging
from datetime import datetime

from grpclib.client import Channel
from grpclib.exceptions import GRPCError

from google.protobuf import json_format

from gym.common.status import Status
from gym.common.tools import Tools

from gym.common.protobuf.gym_grpc import (
    AgentStub,
    MonitorStub,
    ManagerStub,
    PlayerStub,
    InfraStub,
)
from gym.common.protobuf.gym_pb2 import (
    Result,
    Task,
    Report,
    Instruction,
    Snapshot,
    Info,
    Deploy,
)

from gym.common.yang.vnfbd import VNFBD
from gym.common.yang.vnfpp import VNFPP


logger = logging.getLogger(__name__)


class Core:
    def __init__(self, info):
        self.status = Status(info)
        asyncio.create_task(self.greet(info))

    async def _info(self, stub, contacts=[]):
        profile = self.status.profile()

        info = json_format.ParseDict(profile, Info())

        if contacts:
            for contact in contacts:
                info.contacts.append(contact)

        info_reply = {}

        try:
            reply = await stub.Greet(info)
            info_reply = json_format.MessageToDict(
                reply, preserving_proto_field_name=True
            )
        except GRPCError as e:
            logger.info(f"Exception in Greet: {e}")
        except OSError as e:
            logger.info(f"Could not open channel for Greet Info")
            logger.debug(f"Exception: {e}")
        finally:
            return info_reply

    async def _greet(self, role, host, port, contacts=[]):
        channel = Channel(host, port)

        if role == "agent":
            stub = AgentStub(channel)
        elif role == "monitor":
            stub = MonitorStub(channel)
        elif role == "player":
            stub = PlayerStub(channel)
        elif role == "manager":
            stub = ManagerStub(channel)
        else:
            logger.info(
                f"Could not contact role {role} -\
                no Stub class available"
            )
            stub = None

        if stub:
            logger.info(f"Greeting {role} {host}:{port}")
            info = await self._info(stub, contacts)

            if info:
                ack = self.status.info(info)
                if ack:
                    self.status.update_status([role])
            else:
                logger.info(f"Could not greet {host}:{port}")

        channel.close()

    async def info(self, message):
        info = json_format.MessageToDict(message, preserving_proto_field_name=True)

        await self.greet(info)

        ack = self.status.info(info)
        reply = Info()

        if ack:
            role = info.get("role")
            self.status.update_status([role])

        profile = self.status.profile()
        reply = json_format.ParseDict(profile, Info())
        return reply

    async def greet(self, info):
        await asyncio.sleep(1.0)

        roles = ["agent", "monitor", "manager", "player"]
        contacts = self.status.allows(info.get("contacts"))
        contacts_peers = info.get("peers")

        if contacts:
            logger.info(f"Greeting contacts {contacts}")
            for contact in contacts:
                role, address = contact.split("/")
                if role and address:
                    if role in roles:
                        host, port = address.split(":")
                        if host and port:
                            await self._greet(role, host, port, contacts_peers)
                        else:
                            logger.info(
                                f"Host and/or port not provided -\
                                address must be ip:port (e.g., 127.0.0.1:8888)"
                            )
                    else:
                        logger.info(
                            f"Unkown contact role -\
                            it must be one of {roles}"
                        )
                else:
                    logger.info(
                        f"Role and/or address not provided -\
                        contacts must be a list of role/address\
                        (e.g., agent/localhost:5000)"
                    )


class WorkerCore(Core):
    def __init__(self, info):
        Core.__init__(self, info)
        self.tools = Tools()

    async def load(self, folder, types):
        if types == "listeners":
            prefix = "listener_"
        elif types == "probers":
            prefix = "prober_"
        else:
            logger.info(f"Tools not loaded: unkown prefix for {types}")
            return

        tools_cfg = {
            "folder": folder,
            "prefix": prefix,
            "suffix": "py",
            "full_path": True,
        }

        if self.tools.cfg(tools_cfg):
            await self.tools.load()
            logger.info(f"{types} loaded")

            tools = self.tools.info()

            artifacts = {
                types: list(tools.values()),
            }
            self.status.update("artifacts", artifacts)

    def origin(self):
        profile = self.status.profile()
        origin = {
            "id": profile.get("uuid"),
            "role": profile.get("role"),
        }
        return origin

    def snapshot(self, instruction, results):
        snap = Snapshot(id=instruction.get("id"), trial=instruction.get("trial"),)

        snap_dict = {
            "origin": self.origin(),
            "evaluations": results,
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        }

        snap = json_format.ParseDict(snap_dict, snap)
        return snap

    async def instruction(self, message):
        logger.info("Called Instruction")
        instruction = json_format.MessageToDict(
            message, preserving_proto_field_name=True
        )
        logger.info(f"Message: {instruction}")
        actions = instruction.get("actions")
        results = await self.tools.handle(actions)
        snapshot = self.snapshot(instruction, results)
        return snapshot


class ManagerCore(Core):
    def __init__(self, info):
        Core.__init__(self, info)

    def check_uuids(self, locals, requested):
        logger.debug("Verifying requested fit local components")
        local_ids = [peer_uuid for peer_uuid in locals]
        req_ids = [req.uuid for req in requested]

        for req_id in req_ids:
            if req_id not in local_ids:
                logger.debug(
                    f"Component ID requested {req_id} not existent {local_ids}"
                )
                return False
        logger.debug("All requested match locals")
        return True

    def instructions(self, locals, requested, role):
        logger.info(f"Building instructions for {role}")
        instructions = {}

        if role == "agents":
            tools_type = "probers"
        elif role == "monitors":
            tools_type = "listeners"
        else:
            return instructions

        if self.check_uuids(locals, requested):
            for req in requested:

                req_uuid = req.uuid
                peer = locals.get(req_uuid)

                if peer:
                    instruction = Instruction()

                if hasattr(req, tools_type):
                    req_tools = getattr(req, tools_type)

                    action_ids = 0
                    for tool in req_tools:
                        action = instruction.actions.get_or_create(action_ids)
                        action.id = tool.id
                        for k in tool.parameters:
                            action.args[k] = tool.parameters[k]

                        action_ids += 1

                instructions[peer.get("uuid")] = instruction

            logger.info(f"Instructions built: {instructions}")

        else:
            logger.info("Could not build instructions")

        return instructions

    async def callPeer(self, role, address, instruction):
        host, port = address.split(":")
        channel = Channel(host, port)

        if role == "agent":
            stub = AgentStub(channel)
        elif role == "monitor":
            stub = MonitorStub(channel)
        else:
            stub = None
            logger.info(f"Could not contact role {role} - no Stub class")

        if stub:
            reply = await stub.CallInstruction(instruction)
        else:
            reply = Snapshot(id=instruction.id)

        channel.close()
        return reply

    async def callInstructions(self, instructions, peers):
        coros = []

        for uuid, instruction in instructions.items():
            peer = peers.get(uuid)
            role = peer.get("role")
            address = peer.get("address")
            logger.info(f"Calling instruction on: {role} at {address}")

            aw = self.callPeer(role, address, instruction)
            coros.append(aw)

        snaps = await asyncio.gather(*coros, return_exceptions=True)

        peer_uuids = list(instructions.keys())
        valid_snaps = []
        for snap in snaps:
            if isinstance(snap, Exception):
                snap_index = snaps.index(snap)
                uuid = peer_uuids[snap_index]
                instruction = instructions[uuid]
                logger.info(
                    f"Snapshot missing from peer {uuid} in instruction {instruction}"
                )
                logger.debug(f"Snapshot exception: {snap}")
            else:
                valid_snaps.append(snap)

        return valid_snaps

    async def trials(self, task, instructions, peers):
        snapshots = []
        trials = task.trials
        instruction_ids = 1000

        for trial in range(trials):
            logger.info(f"Running trial: {trial} of total {trials}")

            for intruction in instructions.values():
                intruction.id = instruction_ids
                intruction.trial = trial
                instruction_ids += 1

            snaps = await self.callInstructions(instructions, peers)
            snapshots.extend(snaps)

        return snapshots

    def report(self, task, snapshots):
        logger.info(f"Building report for task {task.id} in test {task.test}")

        report = Report(id=task.id, test=task.test)
        report.timestamp.FromDatetime(datetime.now())

        for snap in snapshots:
            report_snap = report.snapshots.get_or_create(snap.id)
            report_snap.CopyFrom(snap)

        return report

    async def task(self, task):
        logger.info("Called Task")
        logger.info(
            f"Message: {json_format.MessageToDict(task, preserving_proto_field_name=True)}"
        )

        peers = {}
        agents_peers = self.status.get_peers("role", "agent", all=True)
        monitors_peers = self.status.get_peers("role", "monitor", all=True)
        peers.update(agents_peers)
        peers.update(monitors_peers)

        instructions = {}
        instructions.update(self.instructions(agents_peers, task.agents, "agents"))
        instructions.update(
            self.instructions(monitors_peers, task.monitors, "monitors")
        )

        snapshots = await self.trials(task, instructions, peers)

        report = self.report(task, snapshots)
        return report


class PlayerCore(Core):
    def __init__(self, info):
        Core.__init__(self, info)

    async def updateGreetings(self, info_str, vnfbd):
        logger.info(f"Updating greetings")
        info = json.loads(info_str)

        if info:
            contacts = vnfbd.contacts(info)
        else:
            contacts = []

        logger.info(f"Contacts: {contacts}")

        if contacts:
            greet_info = {
                "contacts": contacts,
                "peers": contacts,
            }
            await self.greet(greet_info)
        else:
            logger.info(f"No contacts for greetings in info: {info}")

    async def callScenario(self, command, test, vnfbd):
        logger.info(f"Deploying Test Scenario - {command}")

        environment = vnfbd.environment()

        deploy_dict = {
            "id": test,
            "workflow": command,
            "scenario": vnfbd.scenario(),
            "environment": environment,
        }
        deploy = json_format.ParseDict(deploy_dict, Deploy())

        environment = vnfbd.environment()
        env_plugin = environment.get("plugin")
        env_params = env_plugin.get("parameters")
        address = env_params.get("address").get("value")
        host, port = address.split(":")

        channel = Channel(host, port)
        stub = InfraStub(channel)
        built = await stub.Run(deploy)

        if built.error:
            ack = False
            logger.info(f"Scenario not deployed error: {built.error}")
        else:
            ack = True
            logger.info(f"Scenario deployed: {built.ack}")

            info = built.info
            info = info.decode("utf-8")
            await self.updateGreetings(info, vnfbd)

        channel.close()
        return ack

    async def callTask(self, uuid, task):
        logger.info("Calling Test Task")

        peers = self.status.get_peers("role", "manager", all=True)
        peer = peers.get(uuid)
        address = peer.get("address")
        host, port = address.split(":")
        channel = Channel(host, port)
        stub = ManagerStub(channel)
        report = await stub.CallTask(task)
        channel.close()
        return report

    def task(self, vnfbd):
        logger.info("Building vnfbd task template")
        templates = {}
        managers_peers = self.status.get_peers("role", "manager", all=True)

        for uuid, manager in managers_peers.items():
            apparatus = manager.get("apparatus")

            if vnfbd.satisfy(apparatus):
                task_template = vnfbd.task(apparatus)
                templates[uuid] = task_template

        return templates

    async def tests(self, vnfbd):
        logger.info("Running Tests")
        vnfpp = VNFPP()

        tests = vnfbd.tests()
        trials = vnfbd.trials()

        for test in range(tests):

            task_ids = 9000
            for vnfbd_instance in vnfbd.instances():

                if vnfbd_instance.deploy():
                    command = "start"
                    ack = await self.callScenario(command, test, vnfbd_instance)
                else:
                    ack = True

                if ack:
                    task_templates = self.task(vnfbd_instance)

                    for uuid, template in task_templates.items():
                        logger.debug(f"Creating task from template: {template}")

                        task = Task(id=task_ids, test=test, trials=trials)
                        logger.info(
                            f"Task {task_ids} for test {test} with {trials} trials"
                        )
                        json_format.ParseDict(template, task)

                        report = await self.callTask(uuid, task)
                        report_dict = json_format.MessageToDict(
                            report, preserving_proto_field_name=True
                        )
                        logger.info("Received Task Report")
                        vnfpp.add_report(report_dict)
                        task_ids += 1

        logger.info("Finishing Tests")
        if vnfbd.deploy():
            ack = await self.callScenario("stop", 0, vnfbd)

        return vnfpp

    async def layout(self, message):
        logger.info("Received Layout Request")
        result = Result(id=message.id)

        vnfbd = VNFBD()

        inputs = message.inputs
        template = message.template
        vnfbd_model = message.vnfbd

        ok = vnfbd.init(inputs, template, vnfbd_model)

        if ok:
            vnfpp = await self.tests(vnfbd)
            vnfpp_msg = vnfpp.protobuf()
            result.vnfpp.CopyFrom(vnfpp_msg)
        else:
            logger.info("Could not parse vnfbd protobuf message")

        logger.info("Replying Result to Layout Request")
        result.timestamp.FromDatetime(datetime.now())
        return result
