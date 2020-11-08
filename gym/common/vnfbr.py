import os
import json
import logging
import itertools
import pandas as pd
import copy
from numpy import arange

from google.protobuf import json_format
from pyangbind.lib.xpathhelper import YANGPathHelper

from gym.common.yang.utils import Utils
from gym.common.yang import vnf_br
from gym.common.protobuf.vnf_br_pb2 import VnfBr

from gym.common.vnfbd import VNFBD

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

            _min = value.get("min", None)
            _max = value.get("max", None)
            _step = value.get("step", None)

            if _min is not None and _max is not None and _step is not None:

                value_list = list(arange(_min, _max, _step))
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


class VNFBR:
    def __init__(self, data=None):
        self._utils = Utils()
        self._data = data
        self._yang_ph = YANGPathHelper()
        self._yang = vnf_br.vnf_br(path_helper=self._yang_ph)
        self._protobuf = VnfBr()
        self._inputs = Inputs()
        self._outputs = {}
        self._output_ids = 1

    def update_features(self, features, items, value):
        feature_name = "_".join(items)
        feature_value = value
        features[feature_name] = feature_value

    def extract_vnfbd_features_proceedings(self, vnfbd, vnfbd_features):
        proceedings = vnfbd.get("proceedings", {})

        component_types = ["agents", "monitors"]
        tool_types = ["probers", "listeners"]

        for component_type in component_types:

            components = proceedings.get(component_type, {})

            for component in components.values():
                component_id = component.get("uuid")

                for tool_type in tool_types:

                    tools = component.get(tool_type, {})

                    for tool in tools.values():

                        tool_id = str(tool.get("id"))
                        tool_name = tool.get("name")
                        tool_instances = tool.get("instances")

                        feature_items = [
                            "proceedings",
                            component_type,
                            component_id,
                            tool_type,
                            tool_id,
                            "instances",
                        ]
                        self.update_features(
                            vnfbd_features, feature_items, tool_instances
                        )

                        feature_items = [
                            "proceedings",
                            component_type,
                            component_id,
                            tool_type,
                            tool_id,
                            "name",
                        ]
                        self.update_features(vnfbd_features, feature_items, tool_name)

                        parameters = tool.get("parameters", {})

                        for param in parameters.values():
                            param_name = param.get("input")
                            param_value = param.get("value")

                            feature_items = [
                                "proceedings",
                                component_type,
                                component_id,
                                tool_type,
                                tool_id,
                                "parameters",
                                param_name,
                            ]
                            self.update_features(
                                vnfbd_features, feature_items, param_value
                            )

    def extract_vnfbd_features_scenario(self, vnfbd, vnfbd_features):
        scenario = vnfbd.get("scenario", {})

        nodes = scenario.get("nodes", {})
        for node in nodes.values():
            node_id = node.get("id")
            node_features = ["type", "image", "format", "role"]

            for node_feature in node_features:
                feature_items = ["scenario", "nodes", node_id, node_feature]
                feature_value = node.get(node_feature)
                self.update_features(vnfbd_features, feature_items, feature_value)

            node_resources = node.get("resources", {})

            for node_resource_key, node_resource_values in node_resources.items():
                for (
                    node_resource_item,
                    node_resource_value,
                ) in node_resource_values.items():
                    feature_items = [
                        "scenario",
                        "nodes",
                        node_id,
                        "resources",
                        node_resource_key,
                        node_resource_item,
                    ]
                    feature_value = node_resource_value
                    self.update_features(vnfbd_features, feature_items, feature_value)

    def parse_vnfbd(self, vnfbd):
        vnfbd_features = {}

        self.extract_vnfbd_features_proceedings(vnfbd, vnfbd_features)
        self.extract_vnfbd_features_scenario(vnfbd, vnfbd_features)

        return vnfbd_features

    def extract_vnfpp_metrics_series_summary(self, metric_name, metric_values):
        metrics_summary = {}
        data = [{metric_name: value} for value in metric_values]
        df = pd.DataFrame(data=data)
        desc = df[metric_name].describe()
        dict_desc = desc.to_dict()
        col_metrics = {"_".join([metric_name, k]): v for k, v in dict_desc.items()}
        metrics_summary.update(col_metrics)

        return metrics_summary

    def extract_evaluations_metrics(
        self, snap_origin_role, snap_origin_id, evaluations
    ):
        evals_metrics = []

        for evaluation in evaluations.values():
            eval_source = evaluation.get("source")
            eval_source_type = eval_source.get("type")
            eval_source_name = eval_source.get("name")
            eval_instance = evaluation.get("instance")
            eval_repeat = evaluation.get("repeat")
            eval_metrics = evaluation.get("metrics", {})

            instance_feature_name = "_".join(
                [
                    "instance",
                    snap_origin_role,
                    snap_origin_id,
                    eval_source_type,
                    eval_source_name,
                ]
            )
            repeat_feature_name = "_".join(
                [
                    "repeat",
                    snap_origin_role,
                    snap_origin_id,
                    eval_source_type,
                    eval_source_name,
                ]
            )

            if eval_metrics:
                metrics = {
                    instance_feature_name: eval_instance,
                    repeat_feature_name: eval_repeat,
                }
                for metric in eval_metrics.values():
                    metric_name = metric.get("name")
                    metric_scalar = metric.get("scalar", None)
                    metric_series = metric.get("series", None)
                    metric_type = metric.get("type", None)

                    if metric_scalar:
                        metrics[metric_name] = metric_scalar
                    if metric_series:

                        metric_values_raw = [
                            ms.get("value") for ms in metric_series.values()
                        ]

                        metric_values = []

                        for mv in metric_values_raw:
                            if metric_type == "float":
                                metric_values.append(float(mv))

                            elif metric_type == "int":
                                metric_values.append(int(mv))

                            else:
                                metric_values.append(mv)

                        metrics_series_summary = (
                            self.extract_vnfpp_metrics_series_summary(
                                metric_name, metric_values
                            )
                        )

                        metrics.update(metrics_series_summary)

                evals_metrics.append(metrics)

        return evals_metrics

    def extract_snapshots_metrics(self, snapshots):
        snapshots_metrics = []

        snap_metrics_per_trial = {}

        for snapshot in snapshots.values():
            snap_trial = snapshot.get("trial")
            snap_origin = snapshot.get("origin")
            snap_origin_role = snap_origin.get("role")
            snap_origin_id = snap_origin.get("id")

            snaps_metrics = snap_metrics_per_trial.setdefault(snap_trial, [])
            snap_evaluations = snapshot.get("evaluations", {})
            evals_metrics = self.extract_evaluations_metrics(
                snap_origin_role, snap_origin_id, snap_evaluations
            )

            if evals_metrics:
                snaps_metrics.append(evals_metrics)

        for trial, snaps_metrics in snap_metrics_per_trial.items():
            product_snaps_metrics = list(itertools.product(*snaps_metrics))

            for product in product_snaps_metrics:
                joint_snaps_metrics = {"trial": trial}
                for metrics in product:
                    joint_snaps_metrics.update(metrics)

                snapshots_metrics.append(joint_snaps_metrics)

        return snapshots_metrics

    def extract_reports_metrics(self, reports):
        reports_metrics = []

        for report in reports.values():
            report_test = report.get("test")
            report_snapshots = report.get("snapshots", {})

            snaps_metrics = self.extract_snapshots_metrics(report_snapshots)
            for snap_metrics in snaps_metrics:
                snap_metrics["test"] = report_test
                reports_metrics.append(snap_metrics)

        return reports_metrics

    def extract_vnfpp_metrics(self, vnfpp):
        reports = vnfpp.get("reports", {})
        report_metrics = self.extract_reports_metrics(reports)
        return report_metrics

    def parse_vnfpp(self, vnfpp):
        vnfpp_features = self.extract_vnfpp_metrics(vnfpp)
        return vnfpp_features

    def extract_features(self, vnfbd, vnfpp):
        vnfbr_features = []

        vnfbd_features = self.parse_vnfbd(vnfbd)
        vnfpp_features = self.parse_vnfpp(vnfpp)

        for vnfpp_feature in vnfpp_features:
            vnfbr_feature = {**vnfbd_features, **vnfpp_feature}
            vnfbr_features.append(vnfbr_feature)

        return vnfbr_features

    def dataframe(self, filedir=None, save=False):
        filedir = "/tmp/gym/results/" if not filedir else filedir

        filename = "vnfbr-" + str(self._data.get("id", 0)) + ".csv"
        filepath = os.path.normpath(os.path.join(filedir, filename))

        features = self.features()
        df = pd.DataFrame(features)

        if save:
            df.to_csv(filepath)

        return df

    def features(self):
        features = []
        outputs = self._data.get("outputs", {})

        for output in outputs.values():
            vnfbd = output.get("vnfbd")
            vnfpp = output.get("vnfpp")

            output_features = self.extract_features(vnfbd, vnfpp)
            features.extend(output_features)

        return features

    def protobuf(self):
        self._protobuf = VnfBr()
        json_format.ParseDict(self._data, self._protobuf)
        return self._protobuf

    def yang(self):
        self.parse(self._data)
        return self._yang

    def yang_ph(self):
        return self._yang_ph

    def json(self):
        yang_json = self._utils.serialise(self._yang)
        return yang_json

    def parse(self, data=None):
        data = data if data else self._data

        self._yang_ph = YANGPathHelper()
        yang_model = self._utils.parse(
            data, vnf_br, "vnf-br", path_helper=self._yang_ph
        )

        if yang_model:
            logger.info(f"Parsing YANG model data successful")
            self._yang = yang_model
            self._data = data
            return True

        logger.info(f"Could not parse YANG model data")
        return False

    def validate(self, data):
        yang_model = self._utils.parse(data, vnf_br, "vnf-br")

        if yang_model:
            ack = True
            logger.info("Check vnf-br model: valid")
        else:
            ack = False
            logger.info("Check vnf-br model: not valid")

        return ack

    def from_protobuf(self, msg):
        if isinstance(msg, VnfBr):
            logger.info("Parsing vnfbr protobuf data message")

            self._protobuf = msg

            self._data = json_format.MessageToDict(
                self._protobuf, preserving_proto_field_name=True
            )
            return True

        else:
            logger.info("Error: vnf-br message not instance of vnfbr protobuf")
            return False

    def environment(self):
        environment = self._data.get("environment")
        return environment

    def deploy(self):
        environment = self._data.get("environment")
        deploy = environment.get("deploy", False)
        return deploy

    def multiplex(self, input_vars):
        vars_data = {}

        input_vars_dict = dict(input_vars)

        for name, var in input_vars_dict.items():
            var_dict = dict(var)
            values = list(var_dict.get("values"))
            vars_data[name] = values

        inputs_mux = self._inputs.multiplex(vars_data)

        whole_mux_inputs = []
        for input_mux in inputs_mux:

            whole_input = {}
            for var_name, var_value in input_mux.items():
                actual_input = input_vars_dict.get(var_name)
                copy_input = dict(copy.deepcopy(actual_input))
                copy_input["values"] = var_value
                whole_input[var_name] = copy_input

            whole_mux_inputs.append(whole_input)

        return whole_mux_inputs

    def instances(self):
        logger.info("Generating vnf-br instances")
        vnfbr_yang = self.yang()
        environment = self._data.get("environment", {})

        input_vnfbd = vnfbr_yang.inputs.vnfbd
        input_vnfbd_dict = self._utils.dictionary(input_vnfbd)

        input_vars = vnfbr_yang.inputs.variables
        input_mux = self.multiplex(input_vars)

        logger.info(f"Generated: {len(input_mux)} vnf-bd instances")

        for inputs in input_mux:

            vnfbd = VNFBD()
            vnfbd.parse(input_vnfbd_dict)
            vnfbd.set_environment(environment)

            ack = self._utils.fill(vnfbd, inputs)

            if ack:
                vnfbd.set_inputs(inputs)
                yield vnfbd

    def add_output(self, vnfbd, vnfpp):
        output_id = str(self._output_ids)

        inputs = vnfbd.inputs()

        variables = {}
        for vnfbd_input in inputs.values():
            var_name = vnfbd_input.get("name")
            var_value = vnfbd_input.get("values")

            variables[var_name] = {
                "name": var_name,
                "value": var_value,
            }

        output = {
            "id": output_id,
            "variables": variables,
            "vnfbd": vnfbd.dictionary(),
            "vnfpp": vnfpp.dictionary(),
        }

        self._outputs[output_id] = output
        self._output_ids += 1

    def build(self):
        logger.info("Building vnf-br")
        self._data["outputs"] = self._outputs

    def load(self, filepath, yang=True):
        self._data = self._utils.data(filepath, is_json=True)
        if yang:
            self._yang_ph = YANGPathHelper()
            self._utils.load(filepath, self._yang, self._yang_ph, is_json=True)

    def save(self, filedir=None, csv=False):
        filedir = "/tmp/gym/results/" if not filedir else filedir

        filename = "vnfbr-" + str(self._data.get("id", 0)) + ".json"

        filepath = os.path.normpath(os.path.join(filedir, filename))
        try:
            with open(filepath, "+w") as fp:
                json.dump(self._data, fp, indent=4, sort_keys=True)

            if csv:
                self.dataframe(save=True)

        except Exception as ex:
            error = f"VNF-BR save file {filepath} error: {repr(ex)}"
            logger.debug(error)
            ack = False
        else:
            msg = f"VNF-BR save file {filepath} success."
            logger.debug(msg)
            ack = True
        finally:
            return ack
