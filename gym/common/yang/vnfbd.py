import logging
import copy
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
        self._mix_inputs = {}

    def multiplexed(self):
        return self._mix_inputs

    def has_list_value(self, dict_items):
        fields_list = [ field for field,value in dict_items.items() if type(value) is list ]
        return fields_list

    def has_dict_value(self, inputs):
        fields_dict = [ field for field,value in inputs.items() if type(value) is dict ]
        return fields_dict

    def parse_dicts(self):
        fields_list = {}
        fields_dict = self.has_dict_value(self._data)
        
        for field in fields_dict:
            value = self._data.get(field)

            min = value.get("min", None)
            max = value.get("max", None)
            step = value.get("step", None)

            if min is not None and \
                max is not None and \
                step is not None:
                
                
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

    def fill_unique(self, data_lists, unique_lists):
        unique_inputs = []
        
        data_lists_keys = list(data_lists.keys())

        for unique_list in unique_lists:
            unique_input = copy.deepcopy(self._data)

            for field_index in range(len(data_lists_keys)):
                field = data_lists_keys[field_index]
                value = unique_list[field_index] 
                unique_input[field] = value
        
            unique_inputs.append(unique_input)

        return unique_inputs

    def multiplex(self):
        unique_inputs = []
        lists, data_lists = self.lists()
        if lists:
            unique_lists = list(itertools.product(*lists))
            unique_inputs = self.fill_unique(data_lists, unique_lists)
        
        return unique_inputs   

    def init(self, data):
        if self._data:
            self._data = data
            self._mix_inputs = self.multiplex()
            logger.info(f"Input multiplexed: total {len(self._mix_inputs)}")
            return True

        # logger.info(f"Input not multiplexed: No data provided")
        return False


class Proceedings():

    def check_numbers(self, proceedings, apparatus, role):
        available = apparatus.get(role, [])
        required = proceedings.get(role, [])
       
        logger.info(f"Veryfing {role}: \
                    apparatus/available {len(available)} and \
                    proceedings/required {len(required)}")
        
        if required:
            req = True
            if len(required) <= len(available):
                ack = True
            else:
                ack = False    
        else:
            req = False
            ack = True
        
        return (req, ack)
                
    def parse_req_tool_params(self, req_params_ls):
        req_params = { param.get("input"):param.get("value") for param in req_params_ls.values()}
        return req_params

    def _check_tools(self, req_tools, disp_tools):
        avail_tools = dict( [ (available.get('id'), available)  
                                for available in disp_tools] )

        if all([True if tool.get("id") in avail_tools.keys() else False
                for tool in req_tools.values()]):
            
            ack_req_tools = []
            ack_req_tool_ids = []
            
            for req_tool in req_tools.values():
                aval_tool = avail_tools.get(req_tool.get("id"))
                aval_params = aval_tool.get("parameters")
                req_params_ls = req_tool.get("parameters")
                
                req_params = self.parse_req_tool_params(req_params_ls)

                if all([True if param in aval_params else False for param in req_params.keys()]):            
                    ack_req_tool = {
                        "id":req_tool.get("id"),
                        "name": req_tool.get("name", ""),
                        "parameters": req_params,
                    }
                    
                    ack_req_tool_set = [ack_req_tool]
                    req_tool_instances = req_tool.get("instances", 1)
                    if req_tool_instances:
                        ack_req_tool_set = ack_req_tool_set*len(range(int(req_tool_instances)))

                    ack_req_tools.extend(ack_req_tool_set)
                    ack_req_tool_ids.append(req_tool.get("id"))
                else:
                    logger.debug(f"Not all params of tools required {req_params} match with available {aval_params}")
            
            if all([True if tool.get("id") in ack_req_tool_ids else False for tool in req_tools.values()]):
                return ack_req_tools
            else:
                logger.debug(f"Not all tools required {list(req_tools)} were selected {ack_req_tool_ids}")
                return {}
        else:
            logger.debug(f"Not all ids of tools required {list(req_tools.keys())} match with available {list(avail_tools.keys())}")
            return {}

    def _satisfy_tools(self, req_id, aval_id, required, available, selected, selected_ids, tools_type):
        if req_id not in selected_ids and aval_id not in selected_ids.values():
            req_tools = required.get(tools_type)
            avail_tools = available.get("artifacts").get(tools_type)

            ack_req_tools = self._check_tools(req_tools, avail_tools)
        
            if ack_req_tools:
                selected_component = {
                    "uuid": aval_id,
                    tools_type: ack_req_tools
                }               
                selected.append(selected_component)
                selected_ids[req_id] = aval_id
                logger.debug(f"Satisfied {tools_type} for required {req_id} in available {aval_id} ")
                return True
            
            else:
                logger.debug(f"Not satisfied {tools_type} for required {req_id} in available {aval_id} ")
                return False
        
        return False

    def _check_components(self, proceedings, apparatus, role):
        selected_ids = {}
        selected = []
        requisites = proceedings.get(role)
        availables = apparatus.get(role)
        tools_type = 'probers' if role == 'agents' else 'listeners'
        
        logger.debug(f"Checking components")
        logger.debug(f"Checking: proceedings {requisites}")
        logger.debug(f"Checking: apparatus {availables}")

        logger.debug(f'Check {role} components and its {tools_type}')

        availables_ids = dict( [ (available.get('uuid'), available)  
                                            for available in availables ] )
        
        for required in requisites.values():
            req_id = required.get("id")
            
            if req_id in availables_ids:
                available = availables_ids.get(req_id)
                aval_id = req_id
                ack = self._satisfy_tools(req_id, aval_id, required, available, selected, selected_ids, tools_type)

            else:
                for available in availables:
                    aval_id = available.get("uuid")

                    ack = self._satisfy_tools(req_id, aval_id, required, available, selected, selected_ids, tools_type)
                    if ack:
                        break
                    else:
                        pass

        req_choices = selected_ids.keys()

        if all([True if req.get("id") in req_choices else False for req in requisites.values()]):
            logger.debug("All components, tools, and params - successfully selected")
            return selected
            
        logger.debug("NOT all components, tools, and params - selected")
        return {}

    def satisfy(self, apparatus, proceedings):
        structure = {}

        requires_agents, ack_agents = self.check_numbers(proceedings, apparatus, role="agents")
        requires_monitors, ack_monitors = self.check_numbers(proceedings, apparatus, role="monitors")
        
        if ack_agents and ack_monitors:
            
            if requires_agents:
                agents = self._check_components(proceedings, apparatus, 'agents')
                if agents:
                    logger.info(f"Proceedings for agents satisfied")
                    structure['agents'] = agents
                else:
                    logger.info(f"Proceedings for agents not satisfied")
                    return {}
            
            if requires_monitors:
                monitors = self._check_components(proceedings, apparatus, 'monitors')
                if monitors:
                    logger.info(f"Proceedings for monitors satisfied")
                    structure['monitors'] = monitors
                else:
                    logger.info(f"Proceedings for monitors not satisfied")
                    return {}

        else:
            logger.info(f"Not enough apparatus for: agents {ack_agents} and/or monitors {ack_monitors}")

        return structure


class VNFBD():
    def __init__(self, data=None, inputs=None):
        self._data = data
        self._inputs_data = inputs
        self._yang = vnf_bd.vnf_bd(path_helper=YANGPathHelper())
        self._protobuf = VnfBd()
        self.utils = Utils()
        self._inputs = Inputs()
        self._proceedings = Proceedings()
        self.validate(self._data)
        self._inputs.init(self._inputs_data)       
        
    def inputs(self, inputs):
        self._inputs_data = inputs
        self._inputs.init(self._inputs)

    def validate(self, data):
        ack = False
        if data:
            ack = self.utils.validate(data, vnf_bd, "vnf-bd")
            if ack:
                logger.info("vnf-bd model valid")                
            else:
                logger.info("vnf-bd model not valid")
        return ack
   
    def parse(self, data):
        self._yang = self.utils.parse(data, vnf_bd, "vnf-bd")

    def load(self, filepath):
        self._data = self.utils.data(filepath, is_json=True)
        self.utils.load(filepath, self._yang, YANGPathHelper(), is_json=True)
                
    def save(self, filepath):
        self.utils.save(filepath, self._yang)

    def from_protobuf(self, msg):
        if isinstance(msg, VnfBd):
            self._protobuf = msg
            self._data = json_format.MessageToDict(self._protobuf, preserving_proto_field_name=True)
            
            ack = self.validate(self._data)
                
            self.parse(self._data)
            return True
        else:
            logger.info("vnf-bd message not instance of vnfbd protobuf")
        return False

    def protobuf(self):
        self._protobuf = VnfBd()
        json_format.ParseDict(self._data, self._protobuf)
        return self._protobuf

    def yang(self):
        return self._yang

    def satisfy(self, apparatus):
        proceedings = self._data.get("proceedings")
        task_structure = self._proceedings.satisfy(apparatus, proceedings)
        if task_structure:
            return True
        else:
            return False

    def multiplex(self):
        rendered_mux_inputs = []
        mux_inputs = self._inputs.multiplexed()

        if mux_inputs:
            logger.debug(f"Rendering mux inputs - total: {len(mux_inputs)}")
            for inputs in mux_inputs:
                rendered_data = self.utils.render(self._data, inputs)
                rendered_mux_inputs.append(rendered_data)
        else:
            logger.debug(f"Rendering single inputs")
            rendered_data = self.utils.render(self._data, self._inputs_data)
            rendered_mux_inputs.append(rendered_data)

        logger.debug(f"vnfbd multiplexed in: {len(rendered_mux_inputs)} structures")
        logger.debug(f"{rendered_mux_inputs}")
        return rendered_mux_inputs

    def task(self, apparatus):
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

    def contacts(self, info):
        nodes = self._data.get("scenario").get("nodes")
        default_ports = {
            "agent": ":50055",
            "monitor": ":50056",
            "manager": ":50057"
        }
        contacts = []

        agents = []
        monitors = []
        managers = []

        for node in nodes.values():
            role = node.get("role")
            if role == "agent":
                agents.append(node.get("id"))
            if role == "monitor":
                monitors.append(node.get("id"))
            if role == "manager":
                managers.append(node.get("id"))
        
        for host,info in info.items():
            if host in agents:
                contact = "agent/" + info.get("ip") + default_ports.get("agent")
                contacts.append(contact)

            if host in monitors:
                contact = "monitor/" + info.get("ip") + default_ports.get("monitor")
                contacts.append(contact)

            if host in managers:
                contact = "manager/" + info.get("ip") + default_ports.get("manager")
                contacts.append(contact)

        return contacts