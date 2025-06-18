import os
import random

TEMPLATES_DIR = "templates"

def list_templates():
    if not os.path.exists(TEMPLATES_DIR):
        os.makedirs(TEMPLATES_DIR)
    return [f for f in os.listdir(TEMPLATES_DIR) if f.endswith(".txt")]

def load_template(name):
    path = os.path.join(TEMPLATES_DIR, name)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def get_random_template():
    templates = list_templates()
    if not templates:
        return ""
    template_file = random.choice(templates)
    return load_template(template_file)

def fill_template(template, variables: dict):
    for k, v in variables.items():
        template = template.replace("{{" + k + "}}", str(v))
    return template