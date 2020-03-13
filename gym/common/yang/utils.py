import logging
import json
import yaml
from jinja2 import Template, TemplateError
import pyangbind.lib.pybindJSON as pbJ
import pyangbind.lib.serialise as pbS


logger = logging.getLogger(__name__)


class Utils:

    def render(self, source, context):
        rendered = ""
        try:
            j2_tmpl = Template(source)
            rendered = j2_tmpl.render(context)
        except TemplateError as e:
            logger.debug(f"Exception when rendering template: {e}")
            rendered = ""
        finally:            
            logger.debug(f"Rendering: source {source} with context {context} -> {rendered}")
            if rendered:
                return rendered
            else:
                return source

    def save(self, filepath, cls_instance):
        pbJ.dump(
            cls_instance, 
            filepath, 
            indent=4, 
            filter=False, 
            skip_subtrees=[], 
            mode="default")

    def data(self, filepath, is_yaml=False, is_json=False):
        with open(filepath, "r") as fp:           
            if is_json:
                input_data = json.load(fp)
                # logger.debug(f"Loaded data from json file {input_data}")            
            elif is_yaml:
                input_data = yaml.load(fp, Loader=yaml.FullLoader)
                # logger.debug(f"Loaded data from yaml file {input_data}")            
            else:
                logger.info(f"Could not load data from file - specify yaml or json")            
                input_data = {}

            return input_data

    def load(self, filepath, cls_instance, path_helper, is_yaml=False, is_json=False):
            input_data = self.data(filepath, is_yaml, is_json)
            if input_data:

                pbS.pybindJSONDecoder.load_json(
                    input_data, 
                    None, None,
                    obj=cls_instance,
                    path_helper=path_helper,
                    overwrite=True)
            
    def parse(self, data, model, model_name):
        model = pbJ.loads(data, model, model_name)
        return model
        
    def serialise(self, cls_instance):
        data_json = pbJ.dumps(
            cls_instance,
            indent=4, 
            filter=False, 
            skip_subtrees=[], 
            select=False, 
            mode="default")

        return data_json

    def validate(self, data, model, model_name):
        valid = False
        
        try:
            loaded_model = pbJ.loads_ietf(
                            data, model, model_name)
            # valid = True            
        # except AttributeError as e:
        #     valid = False
        #     logger.debug(f"Invalid model - Exception: {e}")
        
        except Exception as e:
            valid = False
            logger.debug(f"Invalid model - Exception: {e}")
        else:
            valid = True
            logger.debug(f"Validated model {loaded_model}")
        finally:
            return valid