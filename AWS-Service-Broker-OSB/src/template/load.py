import json
import cfnlint as cflint
from src.template.model.template_model import Template


class TemplateHelper:
    @staticmethod
    def load_template(template_name: str):
        with open(f'src/config/templates/template_{template_name}.json') as f:
            template_json = json.load(f)
        return Template(template_json)

    @staticmethod
    def update_template(template_name: str, template_values: dict, use_all=True):
        with open(f'src/config/templates/template_{template_name}.json') as f:
            template_json = dict(json.load(f))
        if use_all:
            template_json.update(template_values)
        
        return Template(template_json)
