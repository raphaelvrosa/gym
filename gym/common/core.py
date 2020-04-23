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
        asyncio.create_task(self.greet(info, startup=True))

    async def _info(self, stub, contacts=[]):
        profile = self.status.profile()
        info = json_format.ParseDict(profile, Info())
        
        if contacts:
            for contact in contacts:
                info.contacts.append(contact)

        try:
            reply = await stub.Greet(info)
            info_reply = json_format.MessageToDict(
                reply, preserving_proto_field_name=True
            )
        
        except GRPCError as e:
            logger.info(f"Error in Greet Info")
            logger.debug(f"Exception in Greet: {e}")
            info_reply = {}
        
        except OSError as e:
            logger.info(f"Could not open channel for Greet Info")
            logger.debug(f"Exception: {e}")
            info_reply = {}
        
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
                f"Could not contact role {role} - "
                f"no stub/client available"
            )
            stub = None

        if stub:
            logger.info(f"Greeting {role} at {host}:{port}")
            info = await self._info(stub, contacts)

            if info:
                self.status.add_peer(info)
            else:
                logger.info(f"Could not greet contact at {host}:{port}")

        channel.close()

    async def greet(self, info, startup=False):
        await asyncio.sleep(0.5)
        
        contacts = info.get("contacts")
        allowed_contacts = self.status.allows(contacts)
        
        if allowed_contacts:
            logger.info(f"Greeting contacts: {allowed_contacts}")
        
            for contact in allowed_contacts:
                role, address = contact.split("/")
                host, port = address.split(":")        
                contacts_peers = info.get("peers")
                await self._greet(role, host, port, contacts_peers)
        else:
            logger.info(f"No greetings, contacts empty: {allowed_contacts}")

        if startup:
            logger.info(f"Ready!")

    async def info(self, message):
        logger.info("Received Info")
        logger.debug(f"{message}")
        info = json_format.MessageToDict(message, preserving_proto_field_name=True)

        await self.greet(info)

        self.status.add_peer(info)
        reply = Info()
        profile = self.status.profile()
        reply = json_format.ParseDict(profile, Info())
        
        logger.info("Replying Info")
        logger.debug(f"{reply}")

        return reply


class WorkerCore(Core):
    def __init__(self, info):
        self.tools = Tools()
        asyncio.create_task(self.load_tools(info))
        Core.__init__(self, info)

    def _build_cfg(self, info):
        folder = info.get("folder")
        role = info.get("role")
        
        if role == "monitor":
            prefix = "listener_"
            name = "listeners"
        elif role == "agent":
            prefix = "prober_"
            name = "probers"
        else:
            prefix = None
            name = None

        if prefix:
            tools_cfg = {
                "name": name,
                "folder": folder,
                "prefix": prefix,
                "suffix": "py",
                "full_path": True,
            }
        else:
            tools_cfg = {}

        return tools_cfg

    def _update_status(self, tools_cfg):
        tools = self.tools.info()
        artifacts = {
            tools_cfg.get('name'): list(tools.values()),
        }
        self.status.update("artifacts", artifacts)

    async def load_tools(self, info):
        tools_cfg = self._build_cfg(info)

        if tools_cfg:
            await self.tools.load(tools_cfg)
            self._update_status(tools_cfg)
            logger.info(f"Loaded {info.get('role')} {tools_cfg.get('name')}")
            
        else:
            logger.info(f"Tools not loaded: unkown cfgs for {info.get('role')}")
            
    def origin(self):
        profile = self.status.profile()
        origin = {
            "id": profile.get("uuid"),
            "role": profile.get("role"),
        }
        return origin

    def snapshot(self, instruction, results):
        snapshot = Snapshot(
            id=instruction.get("id"),
            trial=instruction.get("trial"),
        )

        snap = {
            "origin": self.origin(),
            "evaluations": results,
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        }
        
        snapshot = json_format.ParseDict(snap, snapshot)
        return snapshot

    async def instruction(self, message):
        logger.info("Received Instruction")
        logger.debug(f"{message}")

        instruction = json_format.MessageToDict(
            message, preserving_proto_field_name=True
        )
        
        actions = instruction.get("actions")
        results = await self.tools.handle(actions)
        snapshot = self.snapshot(instruction, results)
        
        logger.info(f"Replying Snapshot")
        logger.debug(f"{snapshot}")
        return snapshot


class ManagerCore(Core):
    def __init__(self, info):
        Core.__init__(self, info)

    def actions(self, instruction, req_tools):
        logger.info(f"Building actions")
        logger.debug(f"Tools: {req_tools}")
        
        action_ids = 1
        
        for tool in req_tools:
            action = instruction.actions.get_or_create(action_ids)
            action.id = tool.id
            
            for k in tool.parameters:
                action.args[k] = tool.parameters[k]

            action_ids += 1

    def instruction(self, req_peer, tools_type):
        instruction = None

        if hasattr(req_peer, tools_type):           
            req_tools = getattr(req_peer, tools_type)
            instruction = Instruction()
            self.actions(instruction, req_tools)
        
        return instruction

    def check_uuids(self, locals, requested):
        logger.debug("Verifying if requested workers (agents/monitors) "
                     "fit available components")

        local_ids = [peer_uuid for peer_uuid in locals]
        req_ids = [req.uuid for req in requested]

        for req_id in req_ids:
            if req_id not in local_ids:
                logger.debug(f"Component requested uuid {req_id}"
                             f" not existent/available uuids {local_ids}")
                return False
        
        logger.debug("All requested components match available uuids")
        return True

    def instructions(self, locals, requested, role):
        logger.info(f"Building instructions for {role}")
        instructions = {}
        all_instructions_ok = False

        if role == "agents":
            tools_type = "probers"
        elif role == "monitors":
            tools_type = "listeners"
        else:
            logger.info(f"Instructions not built - "
                        f"Unexistent components available for role {role}")
            return instructions

        if self.check_uuids(locals, requested):
            instructions_built = {}

            for req_peer in requested:
                instruction = self.instruction(req_peer, tools_type)
                
                req_uuid = getattr(req_peer, 'uuid')

                if instruction:
                    instructions_built[req_uuid] = True
                    instructions[req_uuid] = instruction
                    logger.info(f"Instruction built for {role} uuid {req_uuid}")

                else:
                    instructions_built[req_uuid] = False
                    logger.info(f"Instruction not built for {role} uuid {req_uuid} - "
                                f"Could not get tools type {tools_type}")
           
            logger.debug(f"Status of instructions: {instructions_built}")
            all_instructions_ok = all(instructions_built.values())
            
            if all_instructions_ok:
                logger.info(f"All instructions built for {role}")
            else:
                logger.info(f"Not all instructions built for {role}")

        else:
            logger.debug("All requested agents/monitors do not exist and/or not match locals")
            logger.info(f"Could not build instructions for {role}")

        return instructions, all_instructions_ok

    async def callPeer(self, role, address, instruction):
        reply = Snapshot(id=instruction.id)
        
        host, port = address.split(":")
        channel = Channel(host, port)

        if role == "agent":
            stub = AgentStub(channel)
        elif role == "monitor":
            stub = MonitorStub(channel)
        else:
            stub = None
            logger.info(f"Could not contact role {role} - "
                        f"no stub/client available")
            raise(Exception(f"No stub/client available for {role}"))

        try:
            reply = await stub.CallInstruction(instruction)

        except GRPCError as e:
            logger.info(f"Error in instruction call at {address}")
            logger.debug(f"Exception: {e}")
            raise(e)
                    
        except OSError as e:
            logger.info(f"Could not open channel for instruction call at {address}")
            logger.debug(f"Exception: {e}")
            raise(e)
                    
        channel.close()
        return reply

    async def callInstructions(self, instructions, peers):
        logger.info(f"Calling instructions")
        snapshots = []
        coros = []

        for uuid, instruction in instructions.items():
            peer = peers.get(uuid)
            role = peer.get("role")
            address = peer.get("address")
            logger.info(f"Scheduled instruction call on: {role} uuid {uuid} at {address}")

            aw = self.callPeer(role, address, instruction)
            coros.append(aw)

        snaps = await asyncio.gather(*coros, return_exceptions=True)

        peer_uuids = list(instructions.keys())
        

        logger.info(f"Validating snapshots")
        
        for snap in snaps:
            snap_index = snaps.index(snap)
            uuid = peer_uuids[snap_index]
                
            if isinstance(snap, Exception):
                instruction = instructions[uuid]
                logger.info(f"Snapshot fail from uuid {uuid}")
                logger.debug(f"Instruction: {instruction}")
                logger.debug(f"Exception: {snap}")
            else:
                logger.info(f"Snapshot ok from uuid {uuid}")
                snapshots.append(snap)

        return snapshots

    async def trials(self, task, instructions, peers):
        snapshots = []
        trials = task.trials
        _ids = 1001

        logger.info(f"Executing trials {trials} for task {task.id}")

        for trial in range(trials):
            logger.info(f"Trial: {trial} of total {trials}")

            instruction_ids = []
            for intruction in instructions.values():
                intruction.id = _ids
                intruction.trial = trial
                instruction_ids.append(_ids)
                _ids += 1
                
            trial_snapshots = await self.callInstructions(instructions, peers)
            
            snap_ids = [snap.id for snap in trial_snapshots]
            all_snaps_ok = all([True if inst_id in snap_ids else False
                                for inst_id in instruction_ids])

            if all_snaps_ok:
                logger.info(f"All instructions successfull in trial {trial}")
            else:
                logger.info(f"Failed instructions in trial {trial}")

            snapshots.extend(trial_snapshots)

        logger.info(f"Finished trials: {trials}")
        return snapshots

    def report(self, report, snapshots):
        logger.info(f"Building report {report.id} in test {report.test}")

        for snap in snapshots:
            report_snap = report.snapshots.get_or_create(snap.id)
            report_snap.CopyFrom(snap)

        return report

    async def task(self, task):
        logger.info("Received Task")
        logger.debug(f"{task}")
        
        report = Report(id=task.id, test=task.test)
        
        agents_peers = self.status.get_peers("role", "agent", alls=True)
        monitors_peers = self.status.get_peers("role", "monitor", alls=True)
        peers = {**agents_peers, **monitors_peers}
        
        agents_instructions, ai_ok = self.instructions(agents_peers, task.agents, "agents")
        monitors_instructions, mi_ok = self.instructions(monitors_peers, task.monitors, "monitors")
        
        if ai_ok and mi_ok:
            instructions = {**agents_instructions, **monitors_instructions}           
            snapshots = await self.trials(task, instructions, peers)
            report = self.report(report, snapshots)
        else:
            logger.info(f"Test not executed - instructions not ok for agents {ai_ok} and/or monitors {mi_ok}")
            logger.info(f"Could not build report for task {task.id} in test {task.test}")           
            
        logger.info("Replying Report")
        report.timestamp.FromDatetime(datetime.now())
        logger.debug(f"{report}")
       
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
        logger.info("Received Layout")
        logger.debug(f"{message}")

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

        logger.info("Replying Result")
        result.timestamp.FromDatetime(datetime.now())
        
        return result
