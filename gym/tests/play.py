import json
from jinja2 import Template

ctx = {"name":'John Doe'}

temp_dict = {"a": 1, "b": {"c": '{{name}}' }}
temp_json = json.dumps(temp_dict)
template = Template(temp_json)
rendered = template.render(ctx)


# rendered = rendered.encode('utf8')

print(rendered, type(rendered))

new_dict = json.loads(rendered)
print(new_dict)