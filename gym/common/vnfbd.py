import logging
import json
import itertools


from google.protobuf import json_format

from pyangbind.lib.xpathhelper import YANGPathHelper

from gym.common.yang import vnf_bd
from gym.common.yang.utils import Utils

from gym.common.protobuf.vnf_bd_pb2 import VnfBd


logger = logging.getLogger(__name__)


class Proceedings:
    def parse_req_tool_params(self, req_params_ls):
        req_params = {
            param.get("input"): param.get("value") for param in req_params_ls.values()
        }

        return req_params

    def params(self, req_tool, aval_tool):
        logger.info("Evaluating tools parameters")
        ack_req_tool_set = []

        aval_params = aval_tool.get("parameters")
        req_params_ls = req_tool.get("parameters")
        req_sched = req_tool.get("sched", {})

        req_params = self.parse_req_tool_params(req_params_ls)

        if all(
            [True if param in aval_params else False for param in req_params.keys()]
        ):
            ack_req_tool_set = []
            req_tool_instances = int(req_tool.get("instances", 1))

            for req_tool_instance in range(1, req_tool_instances + 1):

                ack_req_tool = {
                    "id": req_tool.get("id"),
                    "name": req_tool.get("name", ""),
                    "parameters": req_params,
                    "sched": req_sched,
                    "instance": req_tool_instance,
                }
                ack_req_tool_set.append(ack_req_tool)

        else:
            logger.debug(
                f"Not all params of tools required {req_params} match with available {aval_params}"
            )
        return ack_req_tool_set

    def tools(self, req_tools, disp_tools):
        logger.info("Evaluating tools")
        tools_ok = {}
        tool_set = []

        avail_tools = dict(
            [(available.get("name"), available) for available in disp_tools]
        )

        for req_tool in req_tools.values():
            req_tool_name = req_tool.get("name")
            tools_ok[req_tool_name] = False
            aval_tool = avail_tools.get(req_tool_name)

            if aval_tool:
                tool_set_ok = self.params(req_tool, aval_tool)

                if tool_set_ok:
                    tool_set.extend(tool_set_ok)
                    tools_ok[req_tool_name] = True
                else:
                    logger.debug(f"No params match for tool id {req_tool_name}")
            else:
                logger.debug(
                    f"No available tool id {req_tool_name} in toolset: {avail_tools.keys()}"
                )

        if all(tools_ok.values()):
            logger.info(f"All tools satisfied")
            return tool_set
        else:
            logger.info(f"Not all tools satisfied: status {tools_ok}")
            return []

    def embed(self, required, available, tools_type):
        if available:
            logger.info(f"Checking toolset for {required.get('uuid')}")
            required_tools = required.get(tools_type)
            available_tools = available.get("artifacts").get(tools_type)
            tool_set = self.tools(required_tools, available_tools)

            if tool_set:
                component = {"uuid": required.get("uuid"), tools_type: tool_set}
                return component

        logger.info(f"No toolset available for {required.get('uuid')}")
        return {}

    def orchestrate(self, role, requisites_ids, availables_ids):
        selected = []
        tools_ok = {}

        tools_type = "probers" if role == "agents" else "listeners"

        for req_uuid, required in requisites_ids.items():
            available = availables_ids.get(
                req_uuid, {}
            )  # TODO: make orch even if req_uuid not in available_ids

            component = self.embed(required, available, tools_type)
            selected.append(component)

            if component:
                tools_ok[req_uuid] = True
                logger.info(
                    f"Satisfied {role}/{tools_type} for required/available {req_uuid}/{req_uuid}"
                )
            else:
                tools_ok[req_uuid] = False
                logger.info(
                    f"Not satisfied {role}/{tools_type} for required/available {req_uuid}/{req_uuid}"
                )

        all_tools_ok = all(tools_ok.values())

        if all_tools_ok:
            logger.info(
                f"All components/tools selected for {role} - status: {tools_ok}"
            )
            return selected
        else:
            logger.info(
                f"Not all components/tools selected for {role} - status: {tools_ok}"
            )
            return []

    def index_by_uuid(self, components):
        indexed = {}
        for component in components:
            uuid = component.get("uuid")
            indexed[uuid] = component
        return indexed

    def components(self, proceedings, apparatus, role):
        logger.debug(f"Building {role} components")

        requisites = proceedings.get(role)
        availables = apparatus.get(role)

        logger.debug(f"Proceedings: {requisites}")
        logger.debug(f"Apparatus: {availables}")

        availables_ids = self.index_by_uuid(availables)
        requisites_ids = self.index_by_uuid(requisites.values())

        selected = self.orchestrate(role, requisites_ids, availables_ids)
        selected_uuids = [component.get("uuid") for component in selected]
        requisites_ok = [
            True if req_uuid in selected_uuids else False for req_uuid in requisites_ids
        ]

        if all(requisites_ok):
            logger.info(f"All components selected for {role}")
            return selected
        else:
            logger.info(
                f"Not all components/tools selected for {role} - check if the proceedings uuid match the available ones"
            )
            logger.debug(f"Available uuids: {availables_ids.keys()}")
            logger.debug(f"Required uuids: {requisites_ids.keys()}")
            return []

    def build(self, ok, role, proceedings, apparatus):
        if ok:
            role_components = self.components(proceedings, apparatus, role)
        else:
            role_components = []
            logger.info(
                f"Failed to build components, no available apparatus for: {role}"
            )

        return role_components

    def verify(self, proceedings, apparatus, role):
        available = apparatus.get(role, [])
        required = proceedings.get(role, [])

        logger.info(
            f"Veryfing {role}: "
            f"apparatus/available {len(available)} and "
            f"proceedings/required {len(required)}"
        )

        req = True if required else False
        ack = True if len(required) <= len(available) else False

        return (req, ack)

    def satisfy(self, apparatus, proceedings):
        structure = {}
        roles_status = {}
        roles = ["agents", "monitors"]

        for role in roles:
            role_status = True

            role_required, role_ok = self.verify(proceedings, apparatus, role=role)

            if role_required:
                role_components = self.build(role_ok, role, proceedings, apparatus)
                structure[role] = role_components

                if not role_components:
                    role_status = False

            roles_status[role] = role_status

        if all(roles_status.values()):
            logger.info("All apparatus roles were satisfied for required proceedings")
            return structure
        else:
            logger.info(
                "Not all apparatus roles were satisfied for required proceedings"
            )
            logger.debug(f"{roles_status}")
            return {}


class VNFBD:
    def __init__(self, data={}):
        self._utils = Utils()
        self._proceedings = Proceedings()
        self._data = data
        self._yang_ph = YANGPathHelper()
        self._yang = vnf_bd.vnf_bd(path_helper=self._yang_ph)
        self._protobuf = VnfBd()
        self._inputs = {}
        self._environment = {}

    def set_environment(self, environment):
        self._environment = environment

    def environment(self):
        return self._environment

    def deploy(self):
        deploy = self._environment.get("deploy", False)
        return deploy

    def set_inputs(self, inputs):
        self._inputs = inputs

    def inputs(self):
        return self._inputs

    def load(self, filepath, yang=True):
        self._data = self._utils.data(filepath, is_json=True)
        if yang:
            self._yang_ph = YANGPathHelper()
            self._utils.load(filepath, self._yang, self._yang_ph, is_json=True)

    def save(self, filepath):
        self._utils.save(filepath, self._yang)

    def dictionary(self):
        data_dict = self._utils.dictionary(self._yang)
        return data_dict

    def data(self):
        return self._data

    def protobuf(self):
        self._protobuf = VnfBd()
        json_format.ParseDict(self._data, self._protobuf)
        return self._protobuf

    def yang(self):
        return self._yang

    def yang_ph(self):
        return self._yang_ph

    def json(self):
        yang_json = self._utils.serialise(self._yang)
        return yang_json

    def build_task(self, apparatus):
        proceedings = self._data.get("proceedings")
        task = self._proceedings.satisfy(apparatus, proceedings)
        return task

    def scenario(self):
        scenario = self._data.get("scenario")
        return scenario

    def tests(self):
        tests_yang = self._yang.experiments.tests.getValue()
        tests = tests_yang.real
        return tests

    def trials(self):
        trials_yang = self._yang.experiments.trials.getValue()
        trials = trials_yang.real
        return trials

    def parse_contacts(self, info, select_contacts):
        contacts = []

        default_ports = {"agent": ":50055", "monitor": ":50056", "manager": ":50057"}
        agents = select_contacts.get("agents")
        monitors = select_contacts.get("monitors")
        managers = select_contacts.get("managers")

        for host, host_info in info.items():
            if host in agents:
                contact = "agent/" + host_info.get("ip") + default_ports.get("agent")
                contacts.append(contact)

            if host in monitors:
                contact = (
                    "monitor/" + host_info.get("ip") + default_ports.get("monitor")
                )
                contacts.append(contact)

            if host in managers:
                contact = (
                    "manager/" + host_info.get("ip") + default_ports.get("manager")
                )
                contacts.append(contact)

        return contacts

    def select_contacts(self, nodes):
        agents = []
        monitors = []
        managers = []

        for node in nodes.values():
            role = node.get("role")
            node_id = node.get("id")

            if role == "agent":
                agents.append(node_id)
            if role == "monitor":
                monitors.append(node_id)
            if role == "manager":
                managers.append(node_id)

        selected = {
            "agents": agents,
            "monitors": monitors,
            "managers": managers,
        }

        return selected

    def contacts(self, info):
        logger.info(f"Parsing vnf-bd scenario contacts info")

        nodes = self._data.get("scenario").get("nodes")

        selected_contacts = self.select_contacts(nodes)
        contacts = self.parse_contacts(info, selected_contacts)

        return contacts

    def parse(self, data=None):
        data = data if data else self._data

        self._yang_ph = YANGPathHelper()
        yang_model = self._utils.parse(
            data, vnf_bd, "vnf-bd", path_helper=self._yang_ph
        )

        if yang_model:
            logger.info(f"Parsing YANG model data successful")
            self._yang = yang_model
            self._data = data
            return True

        logger.info(f"Could not parse YANG model data")
        return False

    def validate(self, data):
        yang_model = self._utils.parse(data, vnf_bd, "vnf-bd")

        if yang_model:
            ack = True
            logger.info("Check vnf-bd model: valid")
        else:
            ack = False
            logger.info("Check vnf-bd model: not valid")

        return ack

    def from_protobuf(self, msg):
        if isinstance(msg, VnfBd):
            logger.info("Parsing vnfbd protobuf data message")

            self._protobuf = msg

            self._data = json_format.MessageToDict(
                self._protobuf, preserving_proto_field_name=True
            )
            self.parse()
            return True

        else:
            logger.info("Error: vnf-bd message not instance of vnfbd protobuf")
            return False

    def init(self, model):
        """Inits the VNF-BD
        validating its content and parsing it
        into a yang model

        Arguments:
            model {VNF-BD} -- A gRPC message of type VNF-BD

        Returns:
            bool -- If the model was validated and
            parsed correctly
        """
        logger.info("Init vnf-bd")

        if self.from_protobuf(model):
            if self.parse():
                return True

        return False
