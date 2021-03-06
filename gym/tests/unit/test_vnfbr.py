import unittest
import os
import json
import logging


from google.protobuf import json_format

from gym.common.vnfbr import VNFBR


LOCAL_FOLDER = os.path.abspath(os.path.dirname(__file__))
FIXTURES = "./fixtures"
FIXTURES_FOLDER = os.path.join(LOCAL_FOLDER, FIXTURES)

logger = logging.getLogger(__name__)


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


class TestVNFBR(unittest.TestCase):
    def test_parse(self):

        vnfbr_data = load_file("vnf-br-003.json")

        vnfbr = VNFBR()
        vnfbr.parse(vnfbr_data)

        vnfbr_yang = vnfbr.yang()
        vnfbr_yang_ph = vnfbr.yang_ph()

        _path = (
            vnfbr_yang.inputs.vnfbd.proceedings.agents["d1"]
            .probers["1"]
            .parameters["pcap"]
            .value._yang_path()
        )

        print(vnfbr_yang_ph.get_unique(_path))
        print("_path", _path)

        instances = vnfbr.instances()
        all_instances = list(instances)
        print(len(all_instances))
        assert len(all_instances) == 8

    def test_save(self):
        vnfbr_data = load_file("vnfbr-001.json")

        vnfbr = VNFBR()
        vnfbr.parse(vnfbr_data)
        vnfbr.save()

    def test_dataframe(self):
        vnfbr_data = load_file("vnfbr-002.json")

        vnfbr = VNFBR()
        vnfbr.parse(vnfbr_data)

        vnfbr_df = vnfbr.dataframe(save=True)
        print(vnfbr_df.info())


if __name__ == "__main__":

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(threadName)s %(name)s %(message)s",
    )
    # unittest.main()
    t = TestVNFBR()
    t.test_parse()
