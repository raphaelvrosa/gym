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

    def load_info(self, vnfbd):
        logger.info("Loading vnf-pp info from vnf-bd")
        pass

    def load_reports(self, reports):
        logger.info("Loading vnf-pp reports")
        for report in reports:
            self.add_report(report)

    def add_report(self, report):
        report_id = report.get("id")
        if "reports" not in self._data:
            self._data["reports"] = {}
        
        self._data["reports"][report_id] = report

    def yang(self):
        return self._yang

    def json(self):
        yang_json = self.utils.serialise(self._yang)
        return yang_json

    def protobuf(self):
        self._protobuf = VnfPp()
        json_format.ParseDict(self._data, self._protobuf)
        return self._protobuf

    def parse(self, data):
        self._yang = self.utils.parse(data, vnf_pp, "vnf-pp")

    def validate(self, data):
        ack = False
        
        if data:
            ack = self.utils.validate(data, vnf_pp, "vnf-pp")
        
            if ack:
                logger.info("Check vnf-pp model: valid")
            else:
                logger.info("Check vnf-pp model: not valid")
        
        return ack

    def from_protobuf(self, msg):
        if isinstance(msg, VnfPp):
            self._protobuf = msg
            self._data = json_format.MessageToDict(
                self._protobuf,
                preserving_proto_field_name=True
            )
            
            ack = self.validate(self._data)
            
            if ack:
                self.parse(self._data)
                return True
        
        logger.info("vnf-pp message not instance of vnfpp protobuf")
        return False
