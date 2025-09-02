import boto3
import argparse
import os
import sys
import logging
import shutil
import uuid
import yaml
import json
import calendar
import time
import configparser
import socket
import hashlib
import csv
import logging
import sys
import subprocess
from subprocess import PIPE, Popen
import threading
from signal import SIGKILL
import signal

# New - S
import os
from src import config
from src.views import CFBroker
import configparser
#from src.app import TemplateEngine
import threading
import openbrokerapi
# New - E

from botocore.exceptions import ClientError

# New - S
#template_engine = TemplateEngine()

APP_CONFIG = os.getenv('APP_SETTINGS', "config.DevConfig")
APP_CONFIG = eval(APP_CONFIG)
# New - E

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,format='%(asctime)s %(message)s')

# Creating an object
logger = logging.getLogger()

# Setting the threshold of logger to DEBUG
logger.setLevel(logging.INFO)



def start_app(script):
    app_command = ['python3', script]
    subprocess.Popen(app_command)
    for thread in threading.enumerate():
        if thread.daemon or thread is threading.current_thread():
            continue
        thread.join()

def join_constructor(loader: yaml.SafeLoader, node: yaml.nodes.ScalarNode) -> str:
    return f"Join {loader.construct_yaml_seq(node)}"

def equals_constructor(loader: yaml.SafeLoader, node: yaml.nodes.ScalarNode) -> str:
    return f"Equal {loader.construct_yaml_seq(node)}"

def if_constructor(loader: yaml.SafeLoader, node: yaml.nodes.ScalarNode) -> str:
    return f"if {loader.construct_yaml_seq(node)}"


def sub_constructor(loader: yaml.SafeLoader, node: yaml.nodes.ScalarNode) -> str:
    return f"Sub {loader.construct_yaml_seq(node)}"


def ref_constructor(loader: yaml.SafeLoader, node: yaml.nodes.ScalarNode) -> str:
    return f"Ref {loader.construct_yaml_seq(node)}"


def getatt_constructor(loader: yaml.SafeLoader, node: yaml.nodes.ScalarNode) -> str:
    return f"GetAtt {loader.construct_yaml_seq(node)}"


def not_constructor(loader: yaml.SafeLoader, node: yaml.nodes.ScalarNode) -> str:
    return f"Not {loader.construct_yaml_seq(node)}"


def get_loader():
    loader = yaml.SafeLoader
    loader.add_constructor("!Equals", equals_constructor)
    loader.add_constructor("!If", if_constructor)
    loader.add_constructor("!Sub", sub_constructor)
    loader.add_constructor("!Ref", ref_constructor)
    loader.add_constructor("!GetAtt", getatt_constructor)
    loader.add_constructor("!Not", not_constructor)
    loader.add_constructor("!Join", join_constructor)
    return loader


def get_yamlobj(template):
    yamlobj = yaml.load(open(template, "rb"), Loader=get_loader())
    return yamlobj

def validate_checksum(original, current):
    orig_file = True
    if original == current:
        logger.info("MD5 validated succeeded")
    else:
        logger.info("MD5 validated Failed.")
        orig_file = False

    return orig_file

def get_env():
    aws_broker_dir = os.getenv("AWS_BROKER_DIR", "ENV_NOT_SET")
    if aws_broker_dir == "ENV_NOT_SET":
        logger.info("Environment Not set 1  ....")
        exit(1)
    elif not os.path.exists(aws_broker_dir):
        logger.info("Directory doesnt exists ...Please create it.")
        exit(1)

    return aws_broker_dir


def get_awsclient():
    #aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID", "<aws_access_key>")
    #aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", "<aws_secret_key>")

    #aws_client = boto3.client('s3', region_name='us-east-1', aws_access_key_id=aws_access_key_id,
    #                          aws_secret_access_key=aws_secret_access_key)
    #aws_client = boto3.client('s3', region_name='us-east-1', aws_access_key_id=aws_access_key_id,
    #                          aws_secret_access_key=aws_secret_access_key)

    session = boto3.Session(profile_name=os.getenv("AWS_USER_PROFILE"))
    aws_client = session.client('s3')

    #boto3.Session(profile_name=os.getenv("AWS_USER_PROFILE"))

    return aws_client

def is_valid_template_file(parser, arg):
    if not os.path.exists(arg):
        parser.error("The file %s does not exist!" % arg)
    else:
        return open(arg, 'r')  # return an open file handle

def set_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument("--run-broker", dest="run_broker", action="store_true", help="Set up and Run broker")
    parser.add_argument("--clean-up", dest="clean_up", action="store_true", help="OClean up broke defaults")

    parser.add_argument("--new-plan", dest="filename", required=False,
                        help="CF template ....", metavar="FILE",
                        type=lambda x: is_valid_file(parser, x))

    return parser.parse_args()


def get_plan_templates(directory):
    templates = dict()
    files = os.listdir(directory)
    for file in files:
        mydir = directory + "/" + file
        if os.path.isdir(mydir):
            myfile = []
            for template in os.listdir(mydir):
                print("File:", template)
                myfile.append(template)
                # templates.append(template)
            templates[mydir] = myfile

    return templates


def get_metadata(template_dir, templates):
    logger.info("Fetching Service metadata from plan bucket and constructing dictonary .....")
    servicedetails = ['name', 'id', 'description', 'tags', 'bindable', 'description']
    servicemetadata = ['displayName', 'imageUrl', 'longDescription', 'providerDisplayName', 'documentationUrl',
                       'supportUrl', 'dashboard_client']

    servicedetails_dict = dict()
    servicemetadata_dict = dict()
    serviceplans_dict = dict()

    service_dict = dict()

    for folder, template in templates.items():
        for file in template:
            templatename = folder + '/' + file
            yamlobj = get_yamlobj(templatename)
            for key, item in yamlobj['Metadata']['AWS::ServiceBroker::Specification'].items():
                if key in servicedetails:
                    servicedetails_dict[key] = item
                if key in servicemetadata:
                    servicemetadata_dict[key] = item

            plan_list = list(yamlobj['Metadata']['AWS::ServiceBroker::Specification']['plans'])
            item = yamlobj['Metadata']['AWS::ServiceBroker::Specification']['plans'][plan_list[0]]
            my_temp_arr = [item]
            serviceplans_dict['plans'] = my_temp_arr
            servicemetadata_update = dict()
            servicemetadata_update['metadata'] = servicemetadata_dict

            #print("MY TEMPLATE NAME:", templatename)
            my_dict = get_ServiceMetaDict(templatename, servicedetails_dict, servicemetadata_update, serviceplans_dict)
            service_dict = dict(service_dict, **my_dict)

    json_object = json.dumps(service_dict, indent=4)
    #logger.info("Final Dictonary for all templates :{json_object}".format(json_object=json_object))

    return service_dict


def dict_exists(item):
    for i in item:
        if isinstance(i, dict):
            return True
    return False


def get_S3_Metatype(details, dictonarytype):
    my_dict = dict()
    for key, item in details.items():
        item_val = item
        if isinstance(item, list) and dictonarytype != "serviceplans":
            if dict_exists(item):
                item_val = str(item[0])
            else:
                sep = "|"
                item_val = sep.join(item)
                item_val = str(item_val)

        if (item == None):
            item_val = 'null'
        if (item == True or item == 'true'):
            item_val = 'true'
        if (item == False or item == 'false'):
            item_val = 'false'

        if dictonarytype == "servicedetails":
            keyname = "service_" + key
        elif dictonarytype == "servicemetadata":
            keyname = "servicemetadata_" + key
        elif dictonarytype == "serviceplan":
            keyname = "serviceplan_" + key
        elif dictonarytype == "serviceplanmetadata":
            keyname = "serviceplanmetadata_" + key
        elif dictonarytype == "serviceplan":
            keyname = "serviceplan_" + key

        my_dict[keyname] = item_val

    return my_dict


def get_ServiceMetaDict(templatename, servicedetails_dict, servicemetadata_update, serviceplans_dict):
    logger.info("Processing plan template :[{templatename}]".format(templatename=templatename))
    key = templatename
    servicedetails_s3_dict = get_S3_Metatype(servicedetails_dict, "servicedetails")
    servicemetadata_s3_dict = get_S3_Metatype(servicemetadata_update["metadata"], "servicemetadata")
    serviceplanmetadata_dict = serviceplans_dict["plans"][0]["metadata"]
    del serviceplans_dict["plans"][0]["metadata"]
    serviceplan_dict = serviceplans_dict["plans"][0]
    serviceplan_s3_dict = get_S3_Metatype(serviceplan_dict, "serviceplan")
    serviceplanmetadata_s3_dict = get_S3_Metatype(serviceplanmetadata_dict, "serviceplanmetadata")
    servicedict = dict()

    mydict = dict(servicedetails_s3_dict, **servicemetadata_s3_dict)
    mydict = dict(mydict, **serviceplan_s3_dict)
    mydict = dict(mydict, **serviceplanmetadata_s3_dict)
    servicedict[key] = mydict

    json_object = json.dumps(mydict, indent=4)

    logger.info("Final Dictonary constructed :{json_object}".format(json_object=json_object))
    return servicedict


def get_numof_plans(plan_type):
    aws_broker_dir = get_env()
    broker_config = aws_broker_dir + '/' + 'config/broker.config'
    # highest_plan_no = 0
    file = ""

    if plan_type == 'standard_plan' or plan_type == 'standard_plan_update':
        file = get_config_values(broker_config, 'FILE_DETAILS', 'standard_plans')
    elif plan_type == 'new_custom_plan':
        file = get_config_values(broker_config, 'FILE_DETAILS', 'custom_plans')
    input_file = open(file, "r+")
    read_buf = csv.reader(input_file)
    highest_plan_no = len(list(read_buf))
    input_file.close()

    return file, highest_plan_no


def get_published_details(plan_no, key, keydata):
    report_string = []
    report_string.append(plan_no)
    report_string.append('"' + os.path.dirname(key) + '"')
    report_string.append('"' + os.path.basename(key) + '"')
    report_string.append('"' + keydata['service_name'] + '"')
    report_string.append('"' + keydata['service_id'] + '"')
    report_string.append('"' + keydata['serviceplan_name'] + '"')
    report_string.append('"' + keydata['serviceplan_id'] + '"')

    my_str = ','.join(str(item) for item in report_string)

    return my_str


def upload_templates(plan_type, templatemetadata, planbucket, object_name=None):
    keys = list(templatemetadata.keys())
    logger.info("Uploading Template to plan bucket {planbucket}".format(planbucket=planbucket))
    """
    for key, val in templatemetadata.items():
        print("KEY:", key)
        print("VALUE:", val)
    """

    file, plan_no = get_numof_plans(plan_type)
    report_file = open(file, "a")

    #s3_client = boto3.client('s3')
    session = boto3.Session(profile_name=os.getenv("AWS_USER_PROFILE"))
    s3_client = session.client('s3')
    

    logger.info("Writing AWS Service Broker specification Service data to plan templates")
    time.sleep(3)

    for key in keys:
        plan_no += 1
        # template = directory + "/" + key
        template = key
        # If S3 object_name was not specified, use template
        if object_name is None:
            keyname = os.path.basename(key)
            metadata = templatemetadata[key]
            # object_name = os.path.basename(template)
        try:
            response = s3_client.upload_file(template, planbucket, keyname)
            s3_client.upload_file(template, planbucket, keyname, ExtraArgs={"Metadata": metadata})
            report_string = get_published_details(plan_no, key, templatemetadata[key])
            report_file.write(report_string + '\n')

        except ClientError as e:
            return False


    return True

def getTrimVal(mystr):
    if mystr == "":
        mystr = ""
    return mystr


def getList(mystr):
    mylist = [x for x in mystr.split('|')]
    return mylist


def getDict(mystr):
    mystr = mystr.replace("'", "\"")
    mylist = json.loads(mystr)
    return mylist


def getServiceDictStandard(mydict, servicedict):
    keys = servicedict.keys()
    mykey = mydict['service_id']
    if mykey in keys:
        plan = {
            "id": mydict["serviceplan_id"],
            "name": mydict["serviceplan_name"],
            "description": mydict["serviceplan_description"],
            "metadata": {"displayname": mydict["serviceplanmetadata_displayname"],
                         "bullets": getList(mydict["serviceplanmetadata_bullets"]),
                         "cost": getDict(mydict["serviceplanmetadata_costs"]),
                         "imageurl": mydict["serviceplanmetadata_imageurl"],
                         "bindable": getTrimVal(mydict["serviceplanmetadata_bindable"]),
                         "planupdateable": getTrimVal(mydict["serviceplanmetadata_planupdateable"])}
        }

        servicedict[mykey]["plans"].append(plan)

    else:
        servicedict[mydict["service_id"]] = {
            "name": mydict["service_name"],
            "id": mydict["service_id"],
            "tags": getList(mydict["service_tags"]),
            "bindable": getTrimVal(mydict["service_bindable"]),
            "description": mydict["service_description"],
            "metadata": {"displayName": mydict["servicemetadata_displayName"],
                         "imageUrl": getTrimVal(mydict["servicemetadata_imageUrl"]),
                         "longDescription": mydict["servicemetadata_longDescription"],
                         "providerDisplayname": mydict["servicemetadata_providerDisplayname"],
                         "documentationUrl": mydict["servicemetadata_documentationUrl"],
                         "supportUrl": mydict["servicemetadata_supportUrl"],
                         "dashboard_client": mydict["servicemetadata_dashboard_client"],
                         },
            "plans": [{
                "id": mydict["serviceplan_id"],
                "name": mydict["serviceplan_name"],
                "description": mydict["serviceplan_description"],
                "metadata": {"displayname": mydict["serviceplanmetadata_displayname"],
                             "bullets": getList(mydict["serviceplanmetadata_bullets"]),
                             "cost": getDict(mydict["serviceplanmetadata_costs"]),
                             "imageurl": mydict["serviceplanmetadata_imageurl"],
                             "bindable": getTrimVal(mydict["serviceplanmetadata_bindable"]),
                             "planupdateable": getTrimVal(mydict["serviceplanmetadata_planupdateable"])}
            }]

        }

    return servicedict


def get_plandata(planbucketname, templatemetadata):
    keys = list(templatemetadata.keys())
    #s3_client = boto3.client('s3')
    session = boto3.Session(profile_name=os.getenv("AWS_USER_PROFILE"))
    s3_client = session.client('s3')
    element_list = []
    for keyname in keys:
        key = os.path.basename(keyname)
        templateurl = "https://{planbucketname}.s3.amazonaws.com/{templatename}".format(planbucketname=planbucketname,
                                                                                        templatename=key)
        response = s3_client.head_object(Bucket=planbucketname, Key=key)
        my_dict = dict()
        my_dict["service_name"] = response["Metadata"]["service_name"]
        my_dict["service_id"] = response["Metadata"]["service_id"]
        my_dict["service_tags"] = response["Metadata"]["service_tags"]
        my_dict["service_bindable"] = response["Metadata"]["service_bindable"]
        my_dict["service_description"] = response["Metadata"]["service_description"]
        my_dict["servicemetadata_displayName"] = response["Metadata"]["servicemetadata_displayname"]
        my_dict["servicemetadata_imageUrl"] = response["Metadata"]["servicemetadata_imageurl"]
        my_dict["servicemetadata_longDescription"] = response["Metadata"]["servicemetadata_longdescription"]
        my_dict["servicemetadata_providerDisplayname"] = response["Metadata"]["servicemetadata_providerdisplayname"]
        my_dict["servicemetadata_documentationUrl"] = response["Metadata"]["servicemetadata_documentationurl"]
        my_dict["servicemetadata_supportUrl"] = response["Metadata"]["servicemetadata_supporturl"]
        my_dict["servicemetadata_dashboard_client"] = response["Metadata"]["servicemetadata_dashboard_client"]
        my_dict["serviceplan_id"] = response["Metadata"]["serviceplan_id"]
        my_dict["serviceplan_name"] = response["Metadata"]["serviceplan_name"]
        my_dict["serviceplan_description"] = response["Metadata"]["serviceplan_description"]
        my_dict["serviceplanmetadata_displayname"] = response["Metadata"]["serviceplanmetadata_displayname"]
        my_dict["serviceplanmetadata_bullets"] = response["Metadata"]["serviceplanmetadata_bullets"]
        my_dict["serviceplanmetadata_costs"] = response["Metadata"]["serviceplanmetadata_costs"]
        my_dict["serviceplanmetadata_imageurl"] = response["Metadata"]["serviceplanmetadata_imageurl"]
        my_dict["serviceplanmetadata_bindable"] = response["Metadata"]["serviceplanmetadata_bindable"]
        my_dict["serviceplanmetadata_planupdateable"] = response["Metadata"]["serviceplanmetadata_planupdateable"]

        if my_dict["serviceplanmetadata_imageurl"] == 'Dummy':
            my_dict["serviceplanmetadata_imageurl"] = templateurl

        element_list.append(my_dict)

    return element_list


def get_Plandetails(service_id, plan_id, catalog_file):
    service_index = -1
    plan_index = -1

    imageurl = ""
    bindable = ""
    planupdateable = ""

    catalog = dict()

    with open(catalog_file, 'r') as openfile:
        # Reading from json file
        json_object = json.load(openfile)
        catalog = json_object

    for service in catalog['catalog']:
        # print("My Service :", service)
        service_index += 1
        if service["id"] == service_id:
            for plan in service["plans"]:
                plan_index += 1
                if plan["id"] == plan_id:
                    imageurl = plan["metadata"]["imageurl"]
                    bindable = plan["metadata"]["bindable"]
                    planupdateable = plan["metadata"]["planupdateable"]

    return service_index, plan_index, bindable, planupdateable, imageurl


def create_clean_dirs(aws_broker_dir):
    logging.info('Creating set up directories')
    # Required Directories
    log_dir = aws_broker_dir + "/" + 'log'
    config_dir = aws_broker_dir + '/' + 'config'
    plan_dir = aws_broker_dir + "/" + 'plans'
    catalog_dir = aws_broker_dir + "/" + 'catalog'
    dirnames = {'log_dir': str(log_dir), 'config_dir': str(config_dir), 'plan_dir': plan_dir,
                'catalog_dir': catalog_dir}

    for directory, directory_path in dirnames.items():
        if os.path.exists(dirnames[directory]):
            for files in os.listdir(dirnames[directory]):
                file = os.path.join(dirnames[directory], files)
                try:
                    shutil.rmtree(file)
                except OSError:
                    os.remove(file)
        else:
            os.mkdir(dirnames[directory])

    return dirnames


def create_clean_files(dirnames):
    # Supported Files
    log_name = dirnames['log_dir'] + "/" + "setup.log"
    broker_config = dirnames['config_dir'] + "/" + "broker.config"
    standard_plans = dirnames['config_dir'] + "/" + "standardplans.published"
    custom_plans = dirnames['config_dir'] + "/" + "customplans.published"
    INI_file = dirnames['config_dir'] + "/" + "broker.INI"
    catalog_file = dirnames['catalog_dir'] + "/" + "catalog.json"

    filenames = {'log_name': log_name, 'broker_config': broker_config, 'standard_plans': standard_plans,
                 'custom_plans': custom_plans, 'INI_file': INI_file, 'catalog_file': catalog_file}

    logging.info('Creating broker environment and set up files ..........')
    for file, filepath in filenames.items():
        if os.path.exists(filenames[file]):
            os.remove(filenames[file])
            open(filenames[file], "a").close()
        else:
            open(filenames[file], "a").close()

    return filenames


def create_broker_bucket(awsobj):
    id = uuid.uuid1()
    gmt = time.gmtime()
    tstamp = calendar.timegm(gmt)
    bucketname = "service-plans" + "-" + str(id) + "-" + str(tstamp)

    # bucketname = "mysample123456random"

    response = awsobj.create_bucket(Bucket=bucketname)
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        return bucketname
    else:
        return 'None'

    return bucketname


def get_port_no(port=5003, max_port=6000):
    # sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    ports = []
    count = 0
    '''
    for portno in range(port, max_port):
        sock = socket.socket()
        sock.bind(('', portno))  # get any available port
        port = sock.getsockname()[1]
        sock.close()
        ports.append(portno)
        count += 1
        if count == 2:
            break
    '''
    ports = ['5000', '5001']
    return ports


def get_quoted_string(my_str):
    my_str = '"' + my_str + '"'
    return my_str


def create_broker_config(filenames, dirnames, update_standard, existing_bucket):
    broker_config = filenames['broker_config']

    awsob = get_awsclient()
    if update_standard:
        plan_bucket = existing_bucket
        return
    else:
        plan_bucket = create_broker_bucket(awsob)

    parser = configparser.ConfigParser()
    # Bucket name entry
    parser.add_section('BROKER_DETAILS')
    parser.set('BROKER_DETAILS', "plan_bucket", get_quoted_string(plan_bucket))
    aws_broker_dir = get_env()
    template_dir = aws_broker_dir + "/aws-open-service-broker-1.0/OneApp/src/config/templates"
    parser.set('BROKER_DETAILS', "template_dir", get_quoted_string(template_dir))

    broker_ports = get_port_no()

    # Change below to take values from webserver.config
    service_broker_url = "http://127.0.0.1:{port}".format(port=broker_ports[0])
    service_broker_url = '"' + service_broker_url + '"'
    template_engine_url = "http://127.0.0.1:{port}".format(port=broker_ports[1])
    template_engine_url = '"' + template_engine_url + '"'

    parser.set('BROKER_DETAILS', "service_broker_url", service_broker_url)
    parser.set('BROKER_DETAILS', "template_engine_url", template_engine_url)

    #  dirnames = {'log_dir': log_dir, 'config_dir': config_dir, 'plan_dir': plan_dir, 'catalog_dir': catalog_dir}
    parser.add_section('DIRECTORY_DETAILS')
    parser.set('DIRECTORY_DETAILS', 'log_dir', get_quoted_string(dirnames['log_dir']))
    parser.set('DIRECTORY_DETAILS', 'config_dir', get_quoted_string(dirnames['config_dir']))
    parser.set('DIRECTORY_DETAILS', 'plan_dir', get_quoted_string(dirnames['plan_dir']))
    parser.set('DIRECTORY_DETAILS', 'catalog_dir', get_quoted_string(dirnames['catalog_dir']))

    # filenames = {'log_name': log_name, 'broker_config': broker_config, 'standard_plans:': standard_plans,
    #            'custom_plans': custom_plans, 'INI_file': INI_file, 'catalog_file': catalog_file}

    src = get_env() + "/aws-open-service-broker-1.0/" + "plandetails.INI"
    dest = dirnames['config_dir'] + "/" + "plandetails.INI"
    shutil.copy(src, dest)

    parser.add_section('FILE_DETAILS')
    parser.set('FILE_DETAILS', 'setup_log_name', get_quoted_string(filenames['log_name']))
    parser.set('FILE_DETAILS', 'standard_plans', get_quoted_string(filenames['standard_plans']))
    parser.set('FILE_DETAILS', 'custom_plans', get_quoted_string(filenames['custom_plans']))
    parser.set('FILE_DETAILS', 'catalog_file', get_quoted_string(filenames['catalog_file']))
    parser.set('FILE_DETAILS', 'INI_file', get_quoted_string(dest))

    fp = open(broker_config, 'w')
    parser.write(fp)
    fp.close()


def write_plan_headers(filenames):
    logger.info("Writing Plan header in published files ......")
    """
    for key, item in filenames.items():
        print(key)
        print(item)
    """
    standard_plan_header = "plan,planfolder,templatename,checksum,servicename,servieid,planname,planid,templateurl\n"
    myfile = filenames['standard_plans']
    fd = open(filenames['standard_plans'], "a")
    fd.write(standard_plan_header)
    fd.close()

    custom_plan_header = "plan,servicename,servieid,planname,planid,templatename,templateurl\n"
    fd = open(filenames['custom_plans'], "a")
    fd.write(custom_plan_header)
    fd.close()


def get_config_values(filename, section, parameter):
    config = configparser.ConfigParser()
    config.read(filename)
    config.sections()
    val = config[section][parameter]
    #print("MY Value:", val)
    val = val.lstrip('"')
    val = val.rstrip('"')
    return val

def create_table(table_name):
    session = boto3.Session(profile_name=os.getenv("AWS_USER_PROFILE"))
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    ops = session.resource("dynamodb")

    try:
        table = ops.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "instance_id", "KeyType": "HASH"},  # Partition key
            ],
            AttributeDefinitions=[
                {"AttributeName": "instance_id", "AttributeType": "S"},
            ],
            ProvisionedThroughput={
                "ReadCapacityUnits": 10,
                "WriteCapacityUnits": 10,
            },
        )
        table.wait_until_exists()
    except ClientError as err:
        logger.error(
            "Couldn't create table %s. Here's why: %s: %s",
            table_name,
            err.response["Error"]["Code"],
            err.response["Error"]["Message"],
        )
        #raise
    else:
        return table


def setup_broker(update_standard, existing_bucket):
    logger.info("Setting up Broker Enviornment and directories")
    aws_broker_dir = get_env()
    section = 'BROKER_DETAILS'
    parameter = 'template_dir'

    create_table("service-broker-ops-state")

    if update_standard:
        aws_broker_dir = get_env()
        broker_config = aws_broker_dir + '/' + 'config/broker.config'
        template_dir = get_config_values(broker_config, section, parameter)
    else:
        dirnames = create_clean_dirs(aws_broker_dir)
        filenames = create_clean_files(dirnames)
        write_plan_headers(filenames)
        create_broker_config(filenames, dirnames, update_standard, existing_bucket)
        template_dir = get_config_values(filenames['broker_config'], section, parameter)

    templates = get_plan_templates(template_dir)

    return template_dir, templates
def shutdownbroker(name):
    # Ask user for the name of process
    pidfile = os.getenv("AWS_BROKER_DIR") + "/" + "process.id"
    try:
        with open(pidfile) as f:
            pid = f.read()
            pid = int(pid)
        os.kill(pid, signal.SIGTERM)
        print(f"Sent SIGTERM signal to process {pid}")
    except OSError:
        print(f"Failed to send SIGTERM signal to process {pid}")
def main():
    standard_plan = False
    standard_plan_update = False
    custom_plan_update = False

    parser = argparse.ArgumentParser()

    parser.add_argument("--run-broker", dest="run_broker", action="store_true",
                        help="Set up and Run broker")

    parser.add_argument("--stop-broker", dest="stop_broker", action="store_true",
                        help="Stop broker")

    parser.add_argument("--clean-up", dest="clean_up", action="store_true",
                        help="Clean up broke defaults")

    parser.add_argument('--update-plan', dest="update_plan", action='store_true',
                        help='Update Plan [Standard/Custom].For standard  Extra arguments'
                             ' of "-f <template> " and "-i <INI file for customer details>" is required')

    parser.add_argument('-f', action="store", nargs=1,
                        help='template file name. Required for both standard and custom plan update',
                        metavar="FILE",
                        type=lambda x: is_valid_template_file(parser, x))

    parser.add_argument('-i', action="store", nargs=1,
                        help='ini file name. Required for custom plan update',
                        metavar="FILE",
                        type=lambda x: is_valid_INI_file(parser, x))

    parser.add_argument('--deprecate-plan', dest="deprecate_plan", action='store_true',
                        help='Deprecate Plan . "-s <serviceid>" and "-p <planid" is required')

    parser.add_argument('-s', action="store", nargs=1,
                        metavar="OPTION",
                        help='Service id')

    parser.add_argument('-p', action="store", nargs=1,
                        metavar="OPTION",
                        help='Plan id')


    args = parser.parse_args()

    if args.update_plan == False or args.f is None or args.i is None:
        print('Correct usage[Custom Plan Update]: aws_service_broker.py '
              '--update-plan -f <templatefilepath> -i <path to INI>')
        print('Correct usage [Standard Plan Update]: aws_service_broker.py --update-plan -f <Template File Path>')
    else:
        print(args.update_plan)
        for i in args.f:
            print("Template file path is ", i)
        for i in args.i:
            print("ini file path is ", i)

    if not len(sys.argv) > 1:
        logging.info("Run $ python setuo_and_run.py --help | -h for help")
        exit(0)

    plan_type = ""

    runbroker = args.run_broker
    cleanup = args.clean_up
    updateplan = args.update_plan
    stopbroker = args.stop_broker

    templates = ""
    template_dir = ""

    existing_bucket = ""
    update_standard = False

    if runbroker:
        # standard_plan = True
        plan_type = 'standard_plan'
        template_dir, templates = setup_broker(update_standard, existing_bucket)
    if cleanup:
        logger.info("Handle cleanup ................")
    if stopbroker:
        logger.info("Stopping broker ................")
        print(sys.argv[0])
        pname = os.path.splitext(sys.argv[0])[0]
        print(pname)
        shutdownbroker(pname)
        sys.exit()


    aws_broker_dir = get_env()
    broker_config = aws_broker_dir + '/' + 'config/broker.config'
    planbucketname = get_config_values(broker_config, 'BROKER_DETAILS', 'plan_bucket')

    if updateplan:
        plan_type = 'standard_plan_update'
        existing_bucket = planbucketname
        update_standard = True
        template_dir, templates = setup_broker(update_standard, existing_bucket)

    logger.info(f"Template DIR:{template_dir}")
    logger.info(f"Templates : {templates}")
    logger.info(f"Bucket Name:{planbucketname}")

    templatemetadata = get_metadata(template_dir, templates)

    upload_templates(plan_type, templatemetadata, planbucketname, object_name=None)
    my_element_list = get_plandata(planbucketname, templatemetadata)

    mydict = dict()
    #logger.info(my_element_list)

    for item in my_element_list:
        mydict = getServiceDictStandard(item, mydict)

    catalog = dict()
    catalog['catalog'] = []
    logger.info("Prepare Service Catalog for all published Services and their plans to AWS Service broker ....")
    for key, items in mydict.items():
        catalog['catalog'].append(items)

    # print(mydict)
    json_object = json.dumps(catalog, indent=4)
    time.sleep(5)
    logger.info("Final Dictonary for all templates : {json_object}".format(json_object=json_object))

    # Writing to catalog directory

    catalog_file = get_config_values(broker_config, 'FILE_DETAILS', 'catalog_file')
    # catalog_file = catalog_file.lstrip('"')
    # catalog_file = catalog_file.rstrip('"')
    with open(catalog_file, "w") as outfile:
        outfile.write(json_object)

    service_id = 'da215457-67ce-4916-b0ab-47420161d654'
    plan_id = 'ab439664-d85b-4dde-a131-5fe860ff529f'

    logger.info("User Request - Service ID:{service_id}".format(service_id=service_id))
    logger.info("User Request - Plan ID:{plan_id}".format(plan_id=plan_id))

    service_index, plan_index, bindable, planupdateable, imageurl = get_Plandetails(service_id, plan_id, catalog_file)

    logger.info("SERVICE Index:{service_index}".format(service_index=service_index))
    logger.info("Plan Index:{plan_index}".format(plan_index=plan_index))
    logger.info("Service Plan Bindable:{bindable}".format(bindable=bindable))
    logging.info("Plan Updatable : {planupdateable}".format(planupdateable=planupdateable))
    logger.info("Image URL :{imageurl}".format(imageurl=imageurl))

    del_bucket = False
    '''
    if del_bucket:
        s3 = boto3.resource('s3')
        bucket = s3.Bucket(planbucketname)
        bucket.objects.all().delete()
        response = bucket.delete(Bucket=planbucketname)
    '''

# New - S
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
    from src.app import TemplateEngine
    template_engine = TemplateEngine()    
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



# New - E



if __name__ == "__main__":
    main()

    # port1 = '5000'
    # port2 = 5001
    #script_path1 = 'OneApp/run_template_engine.py'
    #script_path2 = 'OneApp/run_broker.py'

    #start_app(script_path1)
    #start_app(script_path2)
    #script_path = 'OneApp/run_oneapp.py'
    #start_app(script_path)

    # New - S

    thread1 = threading.Thread(target=run_template_engine)
    thread1.start()

    # run_service_broker()
    thread2 = threading.Thread(target=run_service_broker)
    thread2.start()

    print("This process has the PID", os.getpid())
    pid=str(os.getpid())
    pidfile=os.getenv("AWS_BROKER_DIR") + "/" + "process.id"
    fp = open(pidfile, 'w')
    fp.write('{}'.format(pid))
    fp.close()


    # New - E

