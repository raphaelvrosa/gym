import yaml
import json
from jinja2 import Template

ctx = {"name":'John Doe', "number": 10}

temp_dict = {"a": "{{ number | int }}", "b": {"c": "{{name}}" }}


template = Template(temp_dict)
rendered = template.render(ctx)
new_dict = json.loads(rendered)


# temp_json = json.dumps(temp_dict)
# template = Template(temp_json)
# rendered = template.render(ctx)
# new_dict = json.loads(rendered)

# temp_yaml = yaml.dump(temp_dict)
# template = Template(temp_yaml)
# rendered = template.render(ctx)
# new_dict = yaml.load(rendered, Loader=yaml.FullLoader)


print(type(new_dict.get("a")))
print(new_dict.get("a"))

