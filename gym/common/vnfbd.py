import logging
import copy
import json
import itertools
from numpy import arange

from google.protobuf import json_format

from pyangbind.lib.xpathhelper import YANGPathHelper

from gym.common.yang import vnf_bd
from gym.common.yang.utils import Utils

from gym.common.protobuf.vnf_bd_pb2 import VnfBd


logger = logging.getLogger(__name__)


class Inputs:
    def __init__(self):
        self._data = {}
        self._mux_inputs = []

    def has_list_value(self, dict_items):
        fields_list = [
            field for field, value in dict_items.items() if type(value) is list
        ]
        return fields_list

    def has_dict_value(self, inputs):
        fields_dict = [field for field, value in inputs.items() if type(value) is dict]
        return fields_dict

    def parse_dicts(self):
        fields_list = {}
        fields_dict = self.has_dict_value(self._data)

        for field in fields_dict:
            value = self._data.get(field)

            min = value.get("min", None)
            max = value.get("max", None)
            step = value.get("step", None)

            if min is not None and max is not None and step is not None:

                value_list = list(arange(min, max, step))
                fields_list[field] = value_list

        return fields_list

    def lists(self):
        lists_fields = []
        lists = []

        data_dicts = self.parse_dicts()
        data_lists = self.has_list_value(self._data)

        lists_fields.extend(data_lists)
        lists_fields.extend(data_dicts.keys())

        lists.extend(data_dicts.values())
        lists.extend([self._data.get(field) for field in data_lists])

        return lists, lists_fields

    def fill_unique(self, lists_fields, unique_lists):
        unique_inputs = []

        for unique_list in unique_lists:
            unique_input = copy.deepcopy(self._data)

            for field_index in range(len(lists_fields)):
                field = lists_fields[field_index]
                value = unique_list[field_index]
                unique_input[field] = value

            unique_inputs.append(unique_input)

        return unique_inputs

    def multiplex(self, data):
        logger.info("Multiplexing inputs")
        unique_inputs = []

        self._data = data
        lists, lists_fields = self.lists()

        if lists:
            unique_lists = list(itertools.product(*lists))
            unique_inputs = self.fill_unique(lists_fields, unique_lists)
            self._mux_inputs = unique_inputs

        logger.info(f"Inputs multiplexed: total {len(unique_inputs)}")
        return unique_inputs


class Proceedings:
    def parse_req_tool_params(self, req_params_ls):
        req_params = {
            param.get("input"): param.get("value") for param in req_params_ls.values()
        }

        return req_params

    def params(self, req_tool, aval_tool):
        ack_req_tool_set = []

        aval_params = aval_tool.get("parameters")
        req_params_ls = req_tool.get("parameters")

        req_params = self.parse_req_tool_params(req_params_ls)

        if all(
            [True if param in aval_params else False for param in req_params.keys()]
        ):
            ack_req_tool = {
                "id": req_tool.get("id"),
                "name": req_tool.get("name", ""),
                "parameters": req_params,
            }
            req_tool_instances = req_tool.get("instances", 1)
            ack_req_tool_set = [ack_req_tool] * len(
                range(int(req_tool_instances))
            )

        else:
            logger.debug(
                f"Not all params of tools required {req_params} match with available {aval_params}"
            )

        return ack_req_tool_set

    def tools(self, req_tools, disp_tools):
        tools_ok = {}
        tool_set = []

        avail_tools = dict(
            [(available.get("id"), available) for available in disp_tools]
        )

        for req_tool_id, req_tool in req_tools.items():
            tools_ok[req_tool_id] = False
            aval_tool = avail_tools.get(req_tool_id)

            if aval_tool:
                tool_set_ok = self.params(req_tool, aval_tool)

                if tool_set_ok:
                    tool_set.extend(tool_set_ok)
                    tools_ok[req_tool_id] = True

        if all(tools_ok.values()):
            logger.debug(f"All tools satisfied")
            return tool_set
        else:
            logger.debug(f"Not all tools satisfied: status {tools_ok}")
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
            available = availables_ids.get(req_uuid, {})
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
    def __init__(self, data=None, inputs=None):
        self._utils = Utils()
        self._inputs = Inputs()
        self._proceedings = Proceedings()
        self._data = data
        self._inputs_data = inputs
        self._template = None
        self._yang = vnf_bd.vnf_bd(path_helper=YANGPathHelper())
        self._protobuf = VnfBd()

    def parse_bytes(self, msg):
        msg_dict = {}

        if type(msg) is bytes:
            msg_str = msg.decode("utf32")
            msg_dict = json.loads(msg_str)

        return msg_dict

    def serialize_bytes(self, msg):
        msg_bytes = b""

        if type(msg) is dict:
            msg_str = json.dumps(msg)
            msg_bytes = msg_str.encode("utf32")

        return msg_bytes

    def load(self, filepath, yang=True):
        self._data = self._utils.data(filepath, is_json=True)
        if yang:
            self._utils.load(filepath, self._yang, YANGPathHelper(), is_json=True)

    def save(self, filepath):
        self._utils.save(filepath, self._yang)

    def protobuf(self):
        self._protobuf = VnfBd()
        json_format.ParseDict(self._data, self._protobuf)
        return self._protobuf

    def yang(self):
        self.parse(self._data)
        return self._yang

    def json(self):
        yang_json = self._utils.serialise(self._yang)
        return yang_json

    def multiplex(self, data_template):
        rendered_mux_inputs = []
        mux_inputs = self._inputs.multiplex(self._inputs_data)

        if mux_inputs:
            logger.debug(f"Rendering mux inputs - total: {len(mux_inputs)}")
            for inputs in mux_inputs:
                rendered_data = self._utils.render(data_template, inputs)
                rendered_mux_inputs.append(rendered_data)
        else:
            logger.debug(f"Rendering unique inputs")
            rendered_data = self._utils.render(data_template, self._inputs_data)
            rendered_mux_inputs.append(rendered_data)

        logger.info(f"vnfbd rendered in: {len(rendered_mux_inputs)} templates")
        logger.debug(f"{rendered_mux_inputs}")
        return rendered_mux_inputs

    def instances(self):
        logger.info("Creating vnf-bd instances")

        if self._template:
            templates = self.multiplex(self._template)
        else:
            templates = self.multiplex(self._data)

        for template in templates:
            valid_template = self.validate(template)

            if valid_template:
                yield VNFBD(data=template)

    def build_task(self, apparatus):
        proceedings = self._data.get("proceedings")
        task = self._proceedings.satisfy(apparatus, proceedings)
        return task

    def deploy(self):
        environment = self._data.get("environment")
        deploy = environment.get("deploy", False)
        return deploy

    def scenario(self):
        scenario = self._data.get("scenario")
        return scenario

    def environment(self):
        environment = self._data.get("environment")
        return environment

    def tests(self):
        experiments = self._data.get("experiments")
        tests = experiments.get("tests", 1)
        return tests

    def trials(self):
        experiments = self._data.get("experiments")
        trials = experiments.get("trials", 1)
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
                agents.append()
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

    def parse(self, data):
        self._yang = self._utils.parse(data, vnf_bd, "vnf-bd")

    def validate(self, data):
        ack = False

        if data:
            ack = self._utils.validate(data, vnf_bd, "vnf-bd")

            if ack:
                logger.info("Check vnf-bd model: valid")
            else:
                logger.info("Check vnf-bd model: not valid")

        return ack

    def from_protobuf(self, msg):
        if isinstance(msg, VnfBd):
            logger.info("Set vnf-bd protobuf")

            self._protobuf = msg

            self._data = json_format.MessageToDict(
                self._protobuf, preserving_proto_field_name=True
            )

            return True

        else:
            logger.info("vnf-bd message not instance of vnfbd protobuf")
            return False

    def inputs(self, inputs):
        if inputs:
            logger.info("Set vnf-bd inputs")
            inputs_dict = self.parse_bytes(inputs)
            self._inputs_data = inputs_dict

    def template(self, template):
        if template:
            logger.info("Set vnf-bd template")
            template_dict = self.parse_bytes(template)
            self._template = template_dict

    def init(self, inputs, template, model):
        """Inits the VNF-BD
        validating its content and parsing it
        into a yang model
        Also parses the inputs and template

        Arguments:
            inputs {bytes} -- The possible inputs that
            can be used to be multiplexed and rendered
            into multiple templates
            template {bytes} -- A vnf-bd template, in the
            same format as the vnf-bd model, but containing 
            input fields that can be rendered by inputs.
            model {VNF-BD} -- A gRPC message of type VNF-BD

        Returns:
            bool -- If the model was validated and 
            parsed correctly
        """
        logger.info("Init vnf-bd")

        if self.from_protobuf(model):
            if self.validate(self._data):

                self.parse(self._data)
                self.template(template)
                self.inputs(inputs)

                return True

        return False
