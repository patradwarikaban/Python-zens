import openbrokerapi
import os
from src import config
from src.views import CFBroker
import configparser

APP_CONFIG = os.getenv('APP_SETTINGS', "config.DevConfig")
APP_CONFIG = eval(APP_CONFIG)


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
    broker_config = filename
    config = configparser.ConfigParser()
    config.read(filename)
    config.sections()
    val = config[section][parameter]
    val = val.lstrip('"')
    val = val.rstrip('"')
    return val


aws_broker_dir = get_env()
broker_config = aws_broker_dir + '/' + 'config/broker.config'
service_broker_url = get_config_values(broker_config, 'BROKER_DETAILS', 'service_broker_url')
host, port = service_broker_url.split("//")[-1].split(":")

openbrokerapi.api.serve(
    CFBroker('da215457-67ce-4916-b0ab-47420161d654', 'ab439664-d85b-4dde-a131-5fe860ff529f', APP_CONFIG()),
    credentials=None, host=host, port=int(port))
