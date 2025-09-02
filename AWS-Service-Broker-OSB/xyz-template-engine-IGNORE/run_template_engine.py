import configparser
import os
from src.app import TemplateEngine

template_engine = TemplateEngine()


def get_env():
    AWS_BROKER_DIR = os.getenv("AWS_BROKER_DIR", "ENV_NOT_SET")
    if AWS_BROKER_DIR == "ENV_NOT_SET":
        print("Environment Not set ....")
        exit(1)
    elif os.path.exists(AWS_BROKER_DIR) == False:
        print("Directory doesnt exists ...Please create it.")
        exit(1)

    return AWS_BROKER_DIR


def get_config_values(filename, section, parameter):
    config = configparser.ConfigParser()
    config.read(filename)
    config.sections()
    val = config[section][parameter]
    val = val.lstrip('"')
    val = val.rstrip('"')
    return val


aws_broker_dir = get_env()
broker_config = aws_broker_dir + '/' + 'config/broker.config'
template_engine_url = get_config_values(broker_config, 'BROKER_DETAILS', 'template_engine_url')
host, port = template_engine_url.split("//")[-1].split(":")
print("before serve")
template_engine.serve(debug=True, host=host, port=int(port))
print("after serve")
