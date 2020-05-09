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

from gym.common.vnfbd import VNFBD
from gym.common.vnfpp import VNFPP


logger = logging.getLogger(__name__)


class Core:
    def __init__(self, info):
        self.status = Status(info)
        asyncio.create_task(self.greet(info, startup=True))

    async def _reach(self, stub, contacts=[]):
        """Reaches a stub using the Greet gRPC service call
        handling the info message back into a dict

        Arguments:
            stub {gRPC stub/client} -- A gRPC stub that interfaces
            the info function call in a remote peer

        Keyword Arguments:
            contacts {list} -- The contacts that must be included
            in the info message, so the peer being contacted can
            reach this list of contacts and retrieve their info
            too (default: {[]})

        Returns:
            dict -- The info of the contacted peer to be used
            to build its Identity, and so be added to the peers
            database of the Core status
        """
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
            logger.info(f"Error in reaching: Greet Info")
            logger.debug(f"Exception in Greet: {e}")
            info_reply = {}

        except OSError as e:
            logger.info(f"Could not reach channel for Greet Info")
            logger.debug(f"Exception: {e}")
            info_reply = {}

        finally:
            return info_reply

    async def _contact(self, role, host, port, contacts=[]):
        """Establishes the contact with a remote peer having 
        the provided role (to be able to build the proper stub) at the
        specified host:port params.

        Arguments:
            role {string} -- Role of the peer being contacted
            host {string} -- IP address of the peer being contacted
            port {string} -- Port address of the peer being contacted

        Keyword Arguments:
            contacts {list} -- List of contacts the peer being contact
            must also greet and retrieve info (default: {[]})
        """
        stubs = {
            "agent": AgentStub,
            "monitor": MonitorStub,
            "manager": ManagerStub,
            "player": PlayerStub
        }
        
        channel = Channel(host, port)
        stub_class = stubs.get(role, None)
       
        if stub_class:
            logger.info(f"Contacting {role} at {host}:{port}")
            stub = stub_class(channel)
            info = await self._reach(stub, contacts)

            if info:
                self.status.add_peer(info)
            else:
                logger.info(f"Could not contact {host}:{port}")
        else:
            logger.info(f"Could not contact role {role} - "
                        f"no stub/client available")

        channel.close()

    async def greet(self, info, startup=False):
        """Establishes peering with a contact (another gym component)
        that has the provided fields defined by the info param
        At startup waits a bit so agent/monitor can load its tools 
        before greetings.

        Arguments:
            info {dict} -- Set of information that enables a contact 
            to be reached and become a peer

        Keyword Arguments:
            startup {bool} -- A flag that signs if the App is 
            in startup mode. This function can be called to reach
            contacts in run-time too. (default: {False})
        """
        if startup:
            await asyncio.sleep(0.5)

        contacts = info.get("contacts")
        allowed_contacts = self.status.allows(contacts)

        if allowed_contacts:
            logger.info(f"Greeting contacts: {allowed_contacts}")

            for contact in allowed_contacts:
                role, address = contact.split("/")
                host, port = address.split(":")
                contacts_peers = info.get("peers")
                await self._contact(role, host, port, contacts_peers)
        else:
            logger.info(f"No greetings, contacts empty: {allowed_contacts}")

        if startup:
            logger.info(f"Ready!")

    async def info(self, message):
        """This function is called every time a gym component
        receives an Info gRPC service call. So it adds the peer to its 
        database, and if the message contains contacts, it tries to 
        greet those contacts before replying the Info.
        In summary, gym components exchange Info messages to 
        establish peering, i.e., their add the peer info to its
        peers database.

        Arguments:
            message {Info} -- An Info type of gRPC message containing
            the info about the peer that is contacting/calling

        Returns:
            Info -- An Info type of gRPC message containing the profile
            information of this peer to be sent to the other peer.
        """
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
    """It is the base class of Agent and Monitor.
    So it contains an instance of Tools that can
    load and run probers/listeners.

    Arguments:
        Core {class} -- Agent and Monitor contain all the
        behavior of a Core component (i.e., peer 
        with each other exchanging Info messages)
    """

    def __init__(self, info):
        self.tools = Tools()
        asyncio.create_task(self.load_tools(info))
        Core.__init__(self, info)

    def _build_cfg(self, info):
        """Build the dict config that enables
        the tools (probers or listeners) to be loaded
        from a specific folder

        Arguments:
            info {dict} -- Contains the folder and the role
            of the Agent/Monitor that is loading the tools

        Returns:
            dict -- The set of needed information for the
            probers or listener to be loaded into the tools
            available.
        """
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
        """After loading the tools, their information 
        is stored in the artifacts of a Agent/Monitor
        status (Identity instance)

        Arguments:
            tools_cfg {dict} -- Contains the name of the 
            tools to be stored in the artifacts. 
            I.e., probers or listeners
        """
        tools = self.tools.info()
        artifacts = {
            tools_cfg.get("name"): list(tools.values()),
        }
        self.status.set("artifacts", artifacts)

    async def load_tools(self, info):
        """Loads the tools (probers or listeners)
        based on the info provided

        Arguments:
            info {dict} -- Contains the role of the component
            (agent/monitor) and the folder where the tools are
            located
        """
        tools_cfg = self._build_cfg(info)

        if tools_cfg:
            await self.tools.load(tools_cfg)
            self._update_status(tools_cfg)
            logger.info(f"Loaded {info.get('role')} {tools_cfg.get('name')}")

        else:
            logger.info(f"Tools not loaded: unkown cfgs for {info.get('role')}")

    def origin(self):
        """Just returns the origin of a snapshot
        i.e., the information to be contained inside a snapshot
        that references where it was extracted (component uuid and role)

        Returns:
            dict -- Contains the component uuid and its role
        """
        profile = self.status.profile()
        origin = {
            "id": profile.get("uuid"),
            "role": profile.get("role"),
        }
        return origin

    def snapshot(self, instruction, results):
        """Builds a Snapshot (gRPC message) based on 
        the results extracted from a Instruction (gRPC service call)

        Arguments:
            instruction {dict} -- References the information
            contained in the Instruction message that originated
            the results and the snapshot
            results {list} -- Set of evaluations output of
            tools running the actions contained in the Instruction
            service call

        Returns:
            Snapshot -- A gRPC Snapshot message, containing 
            a timestamp, the origin of the snapshot, and its
            evaluations.
        """
        logger.info("Creating Snapshot")
        
        snapshot = Snapshot(
            id=instruction.get("id"),
            trial=instruction.get("trial")
        )

        snap = {
            "origin": self.origin(),
            "evaluations": results,
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        }

        snapshot = json_format.ParseDict(snap, snapshot)
        return snapshot

    async def instruction(self, message):
        """This function is called when a Instruction
        gRPC service call is made to an Agent/Monitor.
        It executes the Instruction actions using the tools
        available.

        Arguments:
            message {Instruction} -- A Instruction gRPC message

        Returns:
            Snapshot -- A Snapshot gRPC message
        """
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
        """Build the set of actions inside a intruction
        based on the tool id and parameters inside req_tools

        Arguments:
            instruction {Instruction} -- A gRPC message Instruction
            req_tools {list} -- List of tools (id, parameters, sched)
        """
        logger.info(f"Building actions")
        logger.debug(f"Tools: {req_tools}")

        action_ids = 1

        for tool in req_tools:
            action = instruction.actions.get_or_create(action_ids)
            action.id = tool.id

            for k in tool.parameters:
                action.args[k] = tool.parameters[k]

            for s in tool.sched:
                action.sched[s] = tool.sched[s]

            action_ids += 1

    def instruction(self, req_peer, tools_type):
        """Builds a gRPC message of type Instruction
        containing the actions for a specific peer uuid (req_peer)
        defined in the prober/listeners alocated to this peer

        Arguments:
            req_peer {dict} -- Contains a uuid and definitions of 
            tools (probers or listeners) with parameters and values
            thath will be used to compose a Instruction
            tools_type {string} -- Defines the types of tools that
            the req_peer must contain (probers or listeners)

        Returns:
            tuple -- (Instruction, bool) A gRPC message of type 
            Instruction and a bool indicating if the instruction was
            successfuly built or not
        """
        instruction_built = False
        instruction = Instruction()

        if hasattr(req_peer, tools_type):
            req_tools = getattr(req_peer, tools_type, [])

            if req_tools:
                self.actions(instruction, req_tools)
                instruction_built = True

        return instruction, instruction_built

    def build_instructions(self, requested, tools_type):
        """Builds a set of instructions for a particular set
        of peers (agents or monitors) and it tools_type (probers or listeners)

        Arguments:
            requested {list} -- Set of requests for particular peer uuids
            and its tools needed to build an Instruction
            tools_type {string} -- Defines if the tools type is probers or listeners

        Returns:
            tuple -- (dict, bool) A dict containing all the (indexed by uuid) set of 
            Instructions (gRPC messages), and a bool defining if all those instructions
            that were requested were fulfilled
        """
        instructions, instructions_built = {}, {}

        for req_peer in requested:
            instruction, instruction_built = self.instruction(req_peer, tools_type)

            req_uuid = getattr(req_peer, "uuid")

            if instruction_built:
                instructions_built[req_uuid] = True
                instructions[req_uuid] = instruction
                logger.info(f"Instruction built for uuid {req_uuid}")

            else:
                instructions_built[req_uuid] = False
                logger.info(
                    f"Instruction not built for uuid {req_uuid} - "
                    f"Could not get tools type {tools_type}"
                )

        logger.debug(f"Status of instructions per requested uuid: {instructions_built}")
        all_instructions_ok = all(instructions_built.values())
        
        return instructions, all_instructions_ok

    def check_uuids(self, locals, requested):
        """Verifying if (requested) workers (agents/monitors)
        fit available components (locals)

        Arguments:
            locals {list} -- Set of available peer profiles of
            Agents and/or Monitors to which the instructions
            will be send when built
            requested {list} -- Set of requested instructions to be
            built for particuar Agents/Monitors

        Returns:
            bool -- If all uuids requested to build instructions
            match the available peers that Manager has to send
            those instructions
        """
        logger.debug(
            "Verifying if (requested) workers (agents/monitors) "
            "fit available components (locals)"
        )

        local_ids = [peer_uuid for peer_uuid in locals]
        req_ids = [req.uuid for req in requested]

        for req_id in req_ids:
            if req_id not in local_ids:
                logger.debug(
                    f"Failed to check uuids - "
                    f"Component requested uuid {req_id}"
                    f"missing in peer uuids: {local_ids}"
                )

                return False

        logger.debug("All uuids checked - requested match available uuids")
        return True

    def instructions(self, locals, requested, role):
        """Builds the instructions for a particular
        role, considering the available locals (peers)
        Agent/Monitors available to execute the instructions
        and the requested ones

        Arguments:
            locals {list} -- Set of available peer profiles of
            Agents and/or Monitors to which the instructions
            will be send when built
            requested {list} -- Set of requested instructions to be
            built for particuar Agents/Monitors
            role {string} -- Role of the components that the instructions
            will be built

        Returns:
            tuple -- (dict, bool) Set of instructions built and
            if all instructions were built correctly
        """
        logger.info(f"Building instructions for {role}")
        
        instructions, all_instructions_ok = {}, False

        tools_name = {
            "agents": "prober",
            "monitors": "listeners"
        }
        tools_type = tools_name.get(role, None)

        if tools_type:
            if self.check_uuids(locals, requested):
                instructions, all_instructions_ok = self.build_instructions(requested, tools_type)

        if all_instructions_ok:
            logger.info(f"All instructions built for {role}")
        else:
            logger.info(f"Not all instructions built for {role}")

        return instructions, all_instructions_ok
        
    async def call_peer(self, role, address, instruction):
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
            raise (Exception(f"No stub/client available for {role}"))

        try:
            reply = await stub.CallInstruction(instruction)

        except GRPCError as e:
            logger.info(f"Error in instruction call at {address}")
            logger.debug(f"Exception: {e}")
            raise (e)

        except OSError as e:
            logger.info(f"Could not open channel for instruction call at {address}")
            logger.debug(f"Exception: {e}")
            raise (e)

        channel.close()
        return reply

    async def call_instructions(self, instructions, peers):
        """Schedule and calls all the instructions in the proper
        set of peers.
        Not necessarily returns all the snapshots obtained from the
        execution of instructions. As a Instruction might trigger an
        exception, only returns the set of snapshots correctly obtained

        Arguments:
            instructions {dict} -- Set of instructions (indexed by the peer uuid
            where it must be called) to be executed on remote peers
            peers {dict} -- Set of peers where instructions must be executed

        Returns:
            list -- Set of snapshots obtained from the execution of
            instructions
        """
        logger.info(f"Calling instructions")
        snapshots = []
        coros = []

        for uuid, instruction in instructions.items():
            peer = peers.get(uuid)
            role = peer.get("role")
            address = peer.get("address")
            logger.info(
                f"Scheduled instruction call on: {role} uuid {uuid} at {address}"
            )

            aw = self.call_peer(role, address, instruction)
            coros.append(aw)

        logger.info(f"Calling all instructions")
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

    async def trial(self, trial, instructions, peers):
        """Run a single trial - Calls all the instructions
        needed for a trial in the particular peers

        Arguments:
            trial {int} -- Number of the trial being execute
            instructions {dict} -- Set of instructions to be called
            peers {dict} -- Set of peers that instructions will be called
            indexed by uuid

        Returns:
            tuple -- (list, bool) A list of Snapshots obtained from
            running the instructions, and a bool indicating if all 
            the snapshots were obtained from the instructions called
        """
        ids = 1001
        instruction_ids = []

        for intruction in instructions.values():
            intruction.id = ids
            intruction.trial = trial
            instruction_ids.append(ids)
            ids += 1

        trial_snapshots = await self.call_instructions(instructions, peers)

        snap_ids = [snap.id for snap in trial_snapshots]
        snaps_ack = [True if inst_id in snap_ids else False
                    for inst_id in instruction_ids]
        snaps_status = all(snaps_ack)
        
        return trial_snapshots, snaps_status

    async def trials(self, trials, instructions, peers):
        """Runs all the trials needed for a set of instructions
        in the selected peers

        Arguments:
            trials {[type]} -- [description]
            instructions {[type]} -- [description]
            peers {[type]} -- [description]

        Returns:
            [type] -- [description]
        """
        snapshots = []
        
        for trial in range(trials):
            logger.info(f"Trial: {trial} of total {trials}")
            
            trial_snapshots, snaps_status = await self.trial(trial, instructions, peers)

            if snaps_status:
                logger.info(f"All instructions successfull in trial {trial}")
            else:
                logger.info(f"Failed instructions in trial {trial}")

            snapshots.extend(trial_snapshots)

        logger.info(f"Finished trials: {trials}")
        return snapshots

    def report(self, report, snapshots):
        """Adds a set of snapshots into a report

        Arguments:
            report {Report} -- A gRPC message of type Report
            snapshots {list} -- A set of gRPC messages of type
            Snapshot
        """
        logger.info(f"Building report {report.id} in test {report.test}")

        for snap in snapshots:
            report_snap = report.snapshots.get_or_create(snap.id)
            report_snap.CopyFrom(snap)

    async def task(self, task):
        """Function called when a task gRPC service call
        is performed in the Manager component.
        It performs all the lifecycle of a task, i.e., 
        calls all the trials to run instructions in Agents/Monitors
        And then builds a Report containing all the Snapshots obtained

        Arguments:
            task {Task} -- A gRPC message type Task

        Returns:
            Snaphot -- A gRPC message type Snapshot
        """
        logger.info("Received Task")
        logger.debug(f"{task}")

        report = Report(id=task.id, test=task.test)

        agents_peers = self.status.get_peers("role", "agent")
        monitors_peers = self.status.get_peers("role", "monitor")
        
        agents_instructions, ai_ok = self.instructions(
            agents_peers, task.agents, "agents"
        )
        monitors_instructions, mi_ok = self.instructions(
            monitors_peers, task.monitors, "monitors"
        )

        if ai_ok and mi_ok:
            logger.info(f"Executing trials for task {task.id}")
            peers = {**agents_peers, **monitors_peers}
            instructions = {**agents_instructions, **monitors_instructions}
            snapshots = await self.trials(task, instructions, peers)
            self.report(report, snapshots)
        else:
            logger.info(
                f"Test not executed - instructions not ok for agents {ai_ok} and/or monitors {mi_ok}"
            )
            logger.info(
                f"Could not build report for task {task.id} in test {task.test}"
            )

        logger.info("Replying Report")
        report.timestamp.FromDatetime(datetime.now())
        logger.debug(f"{report}")

        return report


class PlayerCore(Core):
    def __init__(self, info):
        Core.__init__(self, info)

    async def updateGreetings(self, info_str, vnfbd):
        """Calls the greet method from the base Core class
        to be used when a new scenario is deployed, so Player
        can contact the Manager component deployed and collects 
        its information: apparatus with set of Agents/Monitors info

        Arguments:
            info_str {string} -- A JSON string containing all the
            encoded management info of interfaces of Manager/Agents/Monitors
            that must execute peering and retrieve info
            vnfbd {VNFBD} -- A VNFBD object instance that establishes
            the contacts proper definition of interfaces that must 
            be reached (i.e., default port numbers) 
        """
        logger.info(f"Greetings to deployed scenario contacts")
        info = json.loads(info_str)

        if info:
            contacts = vnfbd.contacts(info)
        else:
            contacts = []

        logger.debug(f"Contacts: {contacts}")

        if contacts:
            greet_info = {
                "contacts": contacts,
                "peers": contacts,
            }
            await self.greet(greet_info)
        else:
            logger.info(f"No contacts for greetings in scenario deployed")
            logger.debug(f"{info}")

    async def call_scenario(self, command, test, vnfbd):
        """Calls a scenario deployment in the gym-infra component

        Arguments:
            command {string} -- Defines if the scenario being
            called must be in mode start or stop
            test {int} -- The number of the test case that identifies 
            that scenario deployment
            vnfbd {VNFBD} -- A VNFBD object instance from which
            the scenario will be extracted to be deployed

        Returns:
            bool -- If the scenario was deployed correctly/successfuly
            or not
        """
        logger.info(f"Calling test {test} scenario - {command}")

        environment = vnfbd.environment()
        environment = vnfbd.environment()
        env_plugin = environment.get("plugin")
        env_params = env_plugin.get("parameters")
        address = env_params.get("address").get("value")
        host, port = address.split(":")

        deploy_dict = {
            "id": test,
            "workflow": command,
            "scenario": vnfbd.scenario(),
            "environment": environment,
        }
        deploy = json_format.ParseDict(deploy_dict, Deploy())

        try:
            channel = Channel(host, port)
            stub = InfraStub(channel)
            built = await stub.Run(deploy)

        except GRPCError as e:
            logger.info(f"Error in scenario deployment")
            logger.debug(f"{e}")
            ack = False

        except OSError as e:
            logger.info(f"Error in channel for scenario deployment")
            logger.debug(f"{e}")
            ack = False

        else:
            if built.error:
                ack = False
                logger.info(f"Scenario deployed error: {built.error}")
            else:
                ack = True
                logger.info(f"Scenario deployed: {built.ack}")

                info = built.info
                info = info.decode("utf-8")
                await self.updateGreetings(info, vnfbd)
        finally:
            channel.close()

        return ack

    async def call_task(self, uuid, task):
        """Calls a task in a Manager component 
        using a gRPC stub

        Arguments:
            uuid {string} -- The uuid of a Manager component
            that is a peer of Player and by whom the Task will
            be executed
            task {Task} -- A gRPC message of type Task that
            the Manager component being called will have to 
            execute

        Returns:
            dict -- All the information of a Report message
            obtained from a Manager component after running
            the called Task message
        """
        logger.info(f"Calling test task at manager uuid {uuid}")

        peers = self.status.get_peers("role", "manager")
        peer = peers.get(uuid)
        address = peer.get("address")
        host, port = address.split(":")
        channel = Channel(host, port)

        try:
            stub = ManagerStub(channel)
            report_msg = await stub.CallTask(task)

        except GRPCError as e:
            logger.info(f"Error in task call")
            logger.debug(f"{e}")
            report = {}

        except OSError as e:
            logger.info(f"Error in channel for task call")
            logger.debug(f"{e}")
            report = {}

        else:
            report = json_format.MessageToDict(
                report_msg, preserving_proto_field_name=True
            )

        channel.close()
        return report

    def task_template(self, vnfbd):
        """Build a vnfbd task template
        I.e., selects a particular manager (uuid)
        that satisfies all the proceedings (agents/probers
        and/or monitors/listeners) contained in a
        vnfbd instance that will compose a Task message
        to be sent to that selected Manager.

        Arguments:
            vnfbd {VNFBD} -- A VNFBD object instance

        Returns:
            tuple -- (string, dict) The string uuid of the
            manage component where the task template must be
            executed/called and the dict containing the task
            template that will compose a Task message
        """
        logger.info("Building vnfbd task templates")
        uuid, task_template = None, None
        managers_peers = self.status.get_peers("role", "manager")

        for manager_uuid, manager in managers_peers.items():
            apparatus = manager.get("apparatus")
            vnfbd_task_template = vnfbd.build_task(apparatus)

            if vnfbd_task_template:
                logger.info(
                    f"Instance of vnf-bd satisfied by manager uuid {uuid} apparatus"
                )
                return manager_uuid, vnfbd_task_template

        logger.info(f"Instance of vnf-bd not satisfied")
        return uuid, task_template

    async def task(self, test, trials, vnfbd):
        """Run a vnfbd task for a particular test

        Arguments:
            test {int} -- Number of the test case
            trials {int} -- Number of trials that a test case
            must be executed by a Manager component
            vnfbd {VNFBD} -- A VNFBD object instance from which the
            task was generated

        Returns:
            dict -- A report dictionary, containing all the
            (possible) snapshots obtained from the execution of the
            vnfbd task
        """
        uuid, task_template = self.task_template(vnfbd)

        if uuid and task_template:
            logger.info(f"Building task for test {test} with {trials} trials")
            logger.debug(f"Creating task from template: {task_template}")

            task = Task(id=test, test=test, trials=trials)
            json_format.ParseDict(task_template, task)
            report = await self.call_task(uuid, task)

        else:
            logger.info(
                f"Failed to build task for test {test} - no manager apparatus available"
            )
            report = {}

        return report

    async def scenario(self, test, vnfbd_instance, previous_deployment):
        """Handles the deployment of a scenario for a specific instance
        of a vnfbd, in a particular test case

        Arguments:
            test {int} -- The number of the test
            vnfbd_instance {VNFBD} -- A VNFBD object instance
            previous_deployment {bool} -- If a previous deployment exists
            or not

        Returns:
            bool -- If the needed vnfbd scenario is deployed or not
        """
        if previous_deployment:
            ok = await self.call_scenario("stop", test, vnfbd_instance)
            logger.info(f"Stopped previous test {test} deployment scenario: {ok}")

        if vnfbd_instance.deploy():
            vnfbd_deployed = await self.call_scenario("start", test, vnfbd_instance)
            logger.info(f"Started test {test} deployment scenario: {vnfbd_deployed}")
        else:
            vnfbd_deployed = True

        return vnfbd_deployed

    async def tests(self, vnfbd_instance):
        """Executes all the vnfbd instance tests
        Each test requires a scenario deployment
        and the call of all its tasks

        Arguments:
            vnfbd_instance {VNFBD} -- A VNFBD object instance

        Returns:
            tuple -- (list, book) A list of reports output of the
            tasks created from the vnfbd instance, and a bool indicating
            if all the tasks were performed successfuly
        """
        logger.info("Starting vnf-bd instance tests")

        tests = vnfbd_instance.tests()
        trials = vnfbd_instance.tests()
        reports_ok = {}
        reports = []
        vnfbd_deployed = False

        for test in range(tests):
            logger.info(f"Starting test {test} out of {tests} in total")
            reports_ok[test] = False

            vnfbd_deployed = await self.scenario(test, vnfbd_instance, vnfbd_deployed)
            if vnfbd_deployed:

                report = await self.task(test, trials, vnfbd_instance)
                if report:
                    logger.info(f"Received report in test {test}")
                    reports.append(report)
                    reports_ok[test] = True
                else:
                    logger.info(f"Failed report in test {test}")

            else:
                logger.info(f"Deployment of vnf-bd instance failed in test {test}")

        logger.debug(f"Status tests reports: {reports_ok}")
        if all(reports_ok.values()):
            all_reports_ok = True
        else:
            all_reports_ok = False

        logger.info(f"Ending vnf-bd instance tests - all reports ok: {all_reports_ok}")
        return reports, all_reports_ok

    async def vnfbd(self, vnfbd):
        """Executes all the possible instances of 
        a vnfbd. Each instance is obtained from the 
        possible mutiplexing of inputs for a vnfbd

        Arguments:
            vnfbd {VNFBD} -- A VNFBD object instance

        Returns:
            list -- A set of reports obtained from the 
            execution of the tests of vnfbd instances
        """
        logger.info("Starting vnf-bd execution")
        all_reports = []

        for vnfbd_instance in vnfbd.instances():
            reports, ack = await self.tests(vnfbd_instance)
            all_reports.extend(reports)

            if not ack:
                logger.info(f"Error in vnf-bd instance - missing reports")

        logger.info("Finishing vnf-bd execution")
        return all_reports

    def vnfpp(self, vnfbd, reports):
        """From the set of reports obtained
        from the tasks generated and executed based
        on a VNF-BD, creates a VNF-PP

        Arguments:
            vnfbd {VNFBD} -- A VNFBD object instance
            reports {list} -- A list of reports, output 
            of the tasks generated from the execution of 
            the vnfbd

        Returns:
            VNFPP -- A VNFPP object instance containing
            all the reports and the headers obtained from the
            vnfbd.
        """
        vnfpp = VNFPP()
        vnfpp.load_info(vnfbd)
        vnfpp.load_reports(reports)
        return vnfpp

    def vnfbr(self, vnfbd, vnfpp):
        # TODO: Create and fill VNFBR class for result msg
        pass

    async def layout(self, message):
        """Called when a Player receives a gRPC service call 
        of Layout type. It means it must run the VNF-BD inside
        the Layout and return a Result type of gRPC message

        Arguments:
            message {Layout} -- A gRPC message of type Layout
            containing a VNF-BD, its (optional) template, and its
            (optional) inputs

        Returns:
            Result -- A gRPC message of type Result.
            It contains the obtained VNF-PP from the 
            execution of the Layout VNF-BD
        """
        logger.info("Received Layout")
        logger.debug(f"{message}")

        result = Result(id=message.id)
        result.timestamp.FromDatetime(datetime.now())

        inputs = message.inputs
        template = message.template
        vnfbd_model = message.vnfbd

        vnfbd = VNFBD()
        init_ok = vnfbd.init(inputs, template, vnfbd_model)

        if init_ok:
            logger.info("Init vnfbd successful")

            reports = await self.vnfbd(vnfbd)
            vnfpp = self.vnfpp(vnfbd, reports)
            vnfpp_pb = vnfpp.protobuf()
            result.vnfpp.CopyFrom(vnfpp_pb)
            result.timestamp.FromDatetime(datetime.now())

        else:
            logger.info("Could not init vnfbd - empty result")

        logger.info("Replying Result")
        logger.debug(f"{result}")
        return result
