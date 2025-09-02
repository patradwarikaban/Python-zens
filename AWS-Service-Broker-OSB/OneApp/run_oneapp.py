import openbrokerapi
import os
from src import config
from src.views import CFBroker
import configparser
from src.app import TemplateEngine
import threading

template_engine = TemplateEngine()

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



def get_config_values_for_broker(filename, section, parameter):
    broker_config = filename
    config = configparser.ConfigParser()
    config.read(filename)
    config.sections()
    val = config[section][parameter]
    val = val.lstrip('"')
    val = val.rstrip('"')
    return val

def get_config_values_for_template_engine(filename, section, parameter):
    config = configparser.ConfigParser()
    config.read(filename)
    config.sections()
    val = config[section][parameter]
    val = val.lstrip('"')
    val = val.rstrip('"')
    return val

def run_template_engine():
    aws_broker_dir = get_env()
    broker_config = aws_broker_dir + '/' + 'config/broker.config'
    template_engine_url = get_config_values_for_template_engine(broker_config, 'BROKER_DETAILS', 'template_engine_url')
    host_temp_engine, port_temp_engine = template_engine_url.split("//")[-1].split(":")
    print(f"Template Engine is running at 'http://127.0.0.1:5001'")
    template_engine.serve(debug=True, host=host_temp_engine, port=int(port_temp_engine))

def run_service_broker():
    aws_broker_dir = get_env()
    broker_config = aws_broker_dir + '/' + 'config/broker.config'
    service_broker_url = get_config_values_for_broker(broker_config, 'BROKER_DETAILS', 'service_broker_url')
    print(f"Service Broker is running at 'http://127.0.0.1:5000'")
    host_broker, port_broker = service_broker_url.split("//")[-1].split(":")

    openbrokerapi.api.serve(
        CFBroker('da215457-67ce-4916-b0ab-47420161d654', 'ab439664-d85b-4dde-a131-5fe860ff529f', APP_CONFIG()),
        credentials=None, host=host_broker, port=int(port_broker))
    
thread1 = threading.Thread(target=run_template_engine)
thread1.start()

#run_service_broker()
thread2 = threading.Thread(target=run_service_broker)
thread2.start()

# aws_broker_dir = get_env()
# broker_config = aws_broker_dir + '/' + 'config/broker.config'
# service_broker_url = get_config_values_for_broker(broker_config, 'BROKER_DETAILS', 'service_broker_url')
# template_engine_url = get_config_values_for_template_engine(broker_config, 'BROKER_DETAILS', 'template_engine_url')

# host_temp_engine, port_temp_engine = template_engine_url.split("//")[-1].split(":")
# print("Template engine serving")

# template_engine.serve(debug=True, host=host_temp_engine, port=int(port_temp_engine))


# host_broker, port_broker = service_broker_url.split("//")[-1].split(":")

# print("We have the host_broker and port_broker")
# openbrokerapi.api.serve(
#     CFBroker('da215457-67ce-4916-b0ab-47420161d654', 'ab439664-d85b-4dde-a131-5fe860ff529f', APP_CONFIG()),
#     credentials=None, host=host_broker, port=int(port_broker))

# print("Broker served")





