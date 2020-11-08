import unittest
import os
import json

from google.protobuf import json_format

from gym.common.vnfbd import VNFBD


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


class TestVNFBD(unittest.TestCase):
    def test_template(self):
        """Tests the multiplexing of inputs into templates
        and their validation
        """
        vnfbd_template = load_file("template-vnf-bd-003.json")
        vnfbd_inputs = load_file("inputs-vnf-bd-003.json")

        vnfbd = VNFBD()
        vnfbd.load_template(vnfbd_template)
        vnfbd.load_inputs(vnfbd_inputs)

        instances = vnfbd.instances()
        all_instances = list(instances)
        assert len(all_instances) == 18

        instance = all_instances.pop()

        instance_tests = instance.tests()
        assert type(instance_tests) is int

        instance_trials = instance.trials()
        assert type(instance_trials) is int

        # instance_pb = instance.protobuf()
        # print(json_format.MessageToJson(instance_pb))

    def test_inputs(self):
        """Tests the multiplexing of inputs
        """
        vnfbd_inputs = load_file("inputs-vnf-bd-003.json")

        vnfbd = VNFBD()
        mux_inputs = vnfbd._inputs.multiplex(vnfbd_inputs)

        assert len(mux_inputs) == 18

    def test_vnfbd_parse(self):
        """Tests the parse of vnfbd content against YANG model
        """

        vnfbd_data = load_file("vnf-bd-003.json")
        vnfbd = VNFBD()

        # assert vnfbd.parse() == False
        assert vnfbd.parse(vnfbd_data) == True

    def test_vnfbd_protobuf(self):
        """Tests the parse of vnfbd content against YANG model
        """

        vnfbd_data = load_file("vnf-bd-003.json")
        vnfbd = VNFBD()

        # assert vnfbd.parse() == False
        assert vnfbd.parse(vnfbd_data) == True

    def test_vnfbd_yang(self):
        """Tests the parse of vnfbd content against YANG model
        """

        vnfbd_data = load_file("vnf-bd-003.json")
        vnfbd = VNFBD()

        assert vnfbd.parse(vnfbd_data) == True

        vnfbd_yang = vnfbd.yang()
        vnfbd_yang_ph = vnfbd.yang_ph()

        # print(vnfbd_yang)
        # path_name = vnfbd_yang.name._yang_path()
        # name = vnfbd_yang_ph.get_unique(path_name)
        # print(dir(name))
        # print("old name: ", name)
        # name_parent = name._parent
        # name_parent._set_name("testing vnf")
        # print("set name: ", name)
        # new_name = vnfbd_yang_ph.get_unique(path_name)
        # print("new name: ", new_name)

        _name = vnfbd_yang.proceedings.agents["1"].probers["1"].name._yang_name
        _path = vnfbd_yang.proceedings.agents["1"].probers["1"].name._yang_path()
        _obj = vnfbd_yang_ph.get_unique(_path)
        _obj_parent = _obj._parent
        _set_func_name = f"_set_{_name}"
        _set_func = getattr(_obj_parent, _set_func_name)
        _set_func("tcpreplaaaaaay")

        assert "tcpreplaaaaaay" == str(
            vnfbd_yang.proceedings.agents["1"].probers["1"].name
        )


if __name__ == "__main__":
    # unittest.main()

    t = TestVNFBD()
    t.test_vnfbd_yang()
