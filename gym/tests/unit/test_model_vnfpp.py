import logging
import unittest
import os
import json

from google.protobuf import json_format

from gym.common.vnfpp import VNFPP


LOCAL_FOLDER = os.path.abspath(os.path.dirname(__file__))
FIXTURES = "./fixtures"
FIXTURES_FOLDER = os.path.join(LOCAL_FOLDER, FIXTURES)


def parse_filename(filename):
    filepath = os.path.join(FIXTURES_FOLDER, filename)
    return filepath


def load_file(filename):
    try:
        filepath = parse_filename(filename)
        with open(filepath, "+r") as fp:
            json_dict = json.load(fp)
    except Exception as e:
        print(f"Could not load file {filename} - {e}")
        json_dict = {}

    finally:
        return json_dict


class TestVNFPP(unittest.TestCase):
    def test_vnfpp_parse(self):
        """Tests the parse of vnfpp content against YANG model"""

        vnfpp_data = load_file("vnf-pp-000.json")
        vnfpp = VNFPP()

        ack = vnfpp.parse(vnfpp_data)

        # vnfpp_pb = vnfpp.protobuf()
        # print(vnfpp_pb)

        vnfpp_dt = vnfpp.dictionary()
        print(json.dumps(vnfpp_dt, sort_keys=True, indent=4))

        assert ack is True


if __name__ == "__main__":
    # logging.basicConfig(
    #     level=logging.DEBUG,
    #     format="%(asctime)s %(levelname)s %(threadName)s %(name)s %(message)s",
    # )
    unittest.main()
    # t = TestVNFPP()
    # t.test_vnfpp_parse()
