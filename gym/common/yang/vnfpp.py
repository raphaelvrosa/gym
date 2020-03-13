import logging

from google.protobuf import json_format

from pyangbind.lib.xpathhelper import YANGPathHelper

from gym.common.yang import vnf_pp
from gym.common.yang.utils import Utils

from gym.common.protobuf.vnf_pp_pb2 import VnfPp


logger = logging.getLogger(__name__)


class VNFPP():
    def __init__(self):
        self._data = {}
        self._yang = vnf_pp.vnf_pp(path_helper=YANGPathHelper())
        self._protobuf = VnfPp()
        self.utils = Utils()
                
    def add_report(self, report):
        report_id = report.get("id")
        if "reports" not in self._data:
            self._data["reports"] = {}
        
        self._data["reports"][report_id] = report

    def protobuf(self):
        self._protobuf = VnfPp()
        json_format.ParseDict(self._data, self._protobuf)
        return self._protobuf
