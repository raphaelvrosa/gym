import json
from jinja2 import Template

temp_dict = {"a": 1, "b": {"c": '{{name}}' }}
temp_json = json.dumps(temp_dict)
template = Template(temp_json)
rendered = template.render(name='John Doe')


# rendered = rendered.encode('utf8')

print(rendered, type(rendered))

new_dict = json.loads(rendered)
print(new_dict)