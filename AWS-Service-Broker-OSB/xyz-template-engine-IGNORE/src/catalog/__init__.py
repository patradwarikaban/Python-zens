import json
from collections import namedtuple
import configparser
import os
from src.catalog.model.catalog_model import Catalog

__all__ = ["catalogs"]


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
catalog_file = get_config_values(broker_config, 'FILE_DETAILS', 'catalog_file')

with open(catalog_file) as f:
    data = json.load(f)
# catalogs = [namedtuple("Catalog", catalog.keys())(*catalog.values()) for catalog in data["catalogs"]]
catalogs = [Catalog(catalog) for catalog in data["catalog"]]
