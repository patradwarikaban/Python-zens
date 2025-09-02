import os
import requests
import json
from typing import Union, List, Optional
import configparser
from openbrokerapi import errors
from openbrokerapi.api import ServiceBroker
from openbrokerapi.catalog import ServicePlan
from openbrokerapi.service_broker import (
    Service,
    ProvisionDetails,
    ProvisionedServiceSpec,
    DeprovisionDetails,
    DeprovisionServiceSpec,
    ProvisionState, Binding, BindState, UnbindDetails, UnbindSpec, BindDetails, LastOperation, UpdateDetails,
    UpdateServiceSpec, GetBindingSpec, GetInstanceDetailsSpec, OperationState)
from . import aws
from .model import get_model
from .utils import EXECUTOR


class CFBroker(ServiceBroker):
    CREATING = 'CREATING'
    CREATED = 'CREATED'
    BINDING = 'BINDING'
    BOUND = 'BOUND'
    UNBINDING = 'UNBINDING'
    DELETING = 'DELETING'
    DELETED = 'DELETED'

    def __init__(self, service_guid, plan_guid, config):
        self.service_guid = service_guid
        self.plan_guid = plan_guid
        self.model = get_model(config)
        self.service_instances = dict()
        self.aws_cred = config.aws_config
        self.stack = aws.CloudFormationStack(**self.aws_cred)
        self.config = config

    # to check the async cloudfromation stack status in thread
    def stack_waiter(self, stack_name, waiter_name, operation):
        waiter = self.stack.client.get_waiter(waiter_name)
        print(f"Waiting - {waiter_name} - {operation}")
        waiter.wait(StackName=stack_name)
        last_operation = self.last_operation(stack_name, operation)
        print("Completed", last_operation.state)

    def get_service_record(self, instance_id):
        service_record = self.model.get(instance_id)
        if service_record is None:
            raise errors.ErrInstanceDoesNotExist()
        return service_record

    def catalog(self) -> Union[Service, List[Service]]:
        aws_broker_dir = get_env()
        broker_config = aws_broker_dir + '/' + 'config/broker.config'
        template_engine_url = get_config_values(broker_config, 'BROKER_DETAILS', 'template_engine_url')
        payload = {}
        headers = {}
        response = requests.request("GET", template_engine_url + "/v1/catalog", headers=headers, data=payload)
        template_response = json.loads(response.text)  # Template response

        # this_dir = os.path.dirname(__file__)
        # root_dir = os.path.dirname(this_dir)
        # with open(os.path.join(root_dir, "tests", "catalog.json"), "r") as read_file:
        #     data = json.load(read_file)
        # template_response = data['catalogs']

        data = list()
        for services in template_response:
            plans_data = list()
            for plan in services['plans']:
                plans_data.append(ServicePlan(**plan))
            services['plans'] = plans_data
            data.append(Service(**services))
        return data

    def provision(self,
                  instance_id: str,
                  details: ProvisionDetails,
                  async_allowed: bool,
                  **kwargs) -> ProvisionedServiceSpec:

        # TODO: to check the if async_allowed in request
        # if not async_allowed:
        #     raise errors.ErrAsyncRequired()

        if self.model.get(instance_id) is not None:

            record = self.get_service_record(instance_id)

            if record.state == "CREATING":
                return ProvisionedServiceSpec(
                    state=ProvisionState.IS_ASYNC,
                    operation='provision in progress'
                )
            
            elif record.state == "succeeded" and record.stack_status in ["CREATE_COMPLETE", "UPDATE_COMPLETE"] and record.service_id == details.service_id and record.plan_id == details.plan_id and record.context == details.context:
                return ProvisionedServiceSpec(
                    state=ProvisionState.IDENTICAL_ALREADY_EXISTS,
                    operation='already provisioned'
                )
                
            elif record.state == "succeeded" and record.stack_status == ["DELETE_COMPLETE"]:
                    print("Already Deprovisioned: Provisioning again")

            elif record.state == "succeeded" and not async_allowed:
                return ProvisionedServiceSpec(
                    state=ProvisionState.SUCCESSFUL_CREATED,
                    operation='provision successfull'
                )
            else:
                raise errors.ErrInstanceAlreadyExists()

        # TODO: Validate CF
        # from aws_service_broker import get_Plandetails

        provision_details = self.provision_details(
            instance_id, details
        )

        aws_broker_dir = get_env()
        broker_config = aws_broker_dir + '/' + 'config/broker.config'
        catalog_file = get_config_values(broker_config, 'DIRECTORY_DETAILS', 'catalog_dir')
        service_index, plan_index, bindable, planupdateable, imageurl = \
            get_Plandetails(details.service_id, details.plan_id, catalog_file + "/catalog.json")
        service_record = self.model.create_record(instance_id=instance_id, context=details.context,
                                                  stack_status="CREATE_IN_PROGRESS", service_id=details.service_id,
                                                  plan_id=details.plan_id, state=self.CREATING, bind_status=bindable,
                                                  update_status=planupdateable, user="user", plan_details="plan")
        
        service_record.save()

        self.stack.create(provision_details)

        EXECUTOR.submit(self.stack_waiter, instance_id, "stack_create_complete", 'provision')

        return ProvisionedServiceSpec(
            state=ProvisionState.IS_ASYNC,
            operation='provision in progress'
        )

    def last_operation(self, instance_id: str, operation_data: Optional[str], **kwargs) -> LastOperation:
        # TODO: Describe CF and check if is completed
        self.stack.resource_key = "Stacks"

        stack_output = None

        try:
            stack_output = self.stack.describe(instance_id)

        except Exception:
            deleted_stack_list = self.stack.list_deleted_stacks()["StackSummaries"]
            for deleted_stack in deleted_stack_list:
                if deleted_stack["StackName"] == instance_id:
                    stack_output = deleted_stack
                    break

        record = self.model.get(instance_id)

        if not record:
            raise errors.ErrInstanceDoesNotExist()
        
        if not stack_output:
            record.update(actions=[self.model.state.set(OperationState.FAILED.value), self.model.stack_status.set("DO NOT EXIST")])
            return LastOperation(state=OperationState.FAILED, description="FAILED")     
                
        elif stack_output['StackStatus'] in ["CREATE_COMPLETE", "UPDATE_COMPLETE"]:
            if record.state != OperationState.SUCCEEDED.value or record.stack_status == stack_output['StackStatus']:
                record.update(actions=[self.model.state.set(OperationState.SUCCEEDED.value), self.model.stack_status.set(stack_output['StackStatus'])])
            return LastOperation(state=OperationState.SUCCEEDED, description="SUCCEEDED")
        elif stack_output['StackStatus'] in ["DELETE_COMPLETE"]:
            if record.state != OperationState.SUCCEEDED.value or record.stack_status == stack_output['StackStatus']:
                record.update(actions=[self.model.state.set(OperationState.SUCCEEDED.value), self.model.stack_status.set(stack_output['StackStatus'])])
            raise errors.ErrInstanceDeleted()
        elif stack_output['StackStatus'] in ["CREATE_FAILED", "DELETE_FAILED", "UPDATE_FAILED"]:
            if record.state != OperationState.FAILED.value or record.stack_status == stack_output['StackStatus']:
                record.update(actions=[self.model.state.set(OperationState.FAILED.value), self.model.stack_status.set(stack_output['StackStatus'])])
            return LastOperation(state=OperationState.FAILED, description="FAILED")        
        return LastOperation(state=OperationState.IN_PROGRESS, description= stack_output['StackStatus'] )

    def bind(self, instance_id: str, binding_id: str, details: BindDetails, async_allowed: bool, **kwargs) -> Binding:
        # TODO: if created return the CF output and save details in service_record
        service_record = self.get_service_record(instance_id)
        if service_record.state == OperationState.SUCCEEDED:
            return Binding(BindState.SUCCESSFUL_BOUND)

    def unbind(self, instance_id: str, binding_id: str, details: UnbindDetails, async_allowed: bool,
               **kwargs) -> UnbindSpec:
        service_record = self.get_service_record(instance_id)
        if service_record.state == BindState.SUCCESSFUL_BOUND:
            service_record.state = self.CREATED
            return UnbindSpec(False)

    def update(self, instance_id: str, details: UpdateDetails, async_allowed: bool, **kwargs) -> UpdateServiceSpec:
        service_record = self.get_service_record(instance_id)
        if service_record.state == OperationState.IN_PROGRESS:
            raise errors.ErrConcurrentInstanceAccess()
        # TODO: call boto3 api for update CF
        update_details = self.update_details(
            instance_id, details.parameters
        )
        details = self.stack.update(**update_details)
        return UpdateServiceSpec(True)

    def deprovision(self, instance_id: str, details: DeprovisionDetails, async_allowed: bool,
                    **kwargs) -> DeprovisionServiceSpec:
        
        # TODO: to check the if async_allowed in request
        # if not async_allowed:
        #     raise errors.ErrAsyncRequired()

        service_record = self.get_service_record(instance_id)

        if service_record is None:
            raise errors.ErrInstanceDoesNotExist()

        if service_record.state == self.DELETING or service_record.state == self.DELETED:
            return DeprovisionServiceSpec(async_allowed, service_record.state)

        elif service_record.state == OperationState.SUCCEEDED.value and service_record.stack_status == "DELETE_COMPLETE":
            return DeprovisionServiceSpec(
                        is_async=async_allowed,
                        operation='already deprovision'
                    )

        deprovision_details = self.deprovision_details(instance_id)
        self.stack.delete(StackName=deprovision_details)
        
        service_record.update(actions=[self.model.state.set(self.DELETING)])
        service_record.update(actions=[self.model.stack_status.set("DELETE_IN_PROGRESS")])
        service_record.save()

        if async_allowed:
            EXECUTOR.submit(self.stack_waiter, instance_id, "stack_delete_complete", 'deprovision')

        return DeprovisionServiceSpec(
            is_async=async_allowed,
            operation='deprovision is in progress'
        )

    def get_instance(self, instance_id: str, **kwargs) -> GetInstanceDetailsSpec:
        pass

    def get_binding(self, instance_id: str, binding_id: str, **kwargs) -> GetBindingSpec:
        pass

    def last_binding_operation(self, instance_id: str, binding_id: str, operation_data: Optional[str],
                               **kwargs) -> LastOperation:
        pass

    def build_tags(
            self, service_id=None, plan_id=None, organization_guid=None, space_guid=None
    ):
        tags = {"Managed by": self.config.APP_NAME}
        if service_id:
            tags["Service ID"] = service_id
        if plan_id:
            tags["Plan ID"] = plan_id
        if organization_guid:
            tags["Organization ID"] = organization_guid
        if space_guid:
            tags["Space ID"] = space_guid
        if self.config.TESTING:
            tags["TestRunGUID"] = self.config.TEST_RUN_GUID
        return tags

    def provision_details(self, instance_id, details):
        data = {"StackName": instance_id}
        aws_broker_dir = get_env()
        broker_config = aws_broker_dir + '/' + 'config/broker.config'
        template_engine_url = get_config_values(broker_config, 'BROKER_DETAILS', 'template_engine_url')
        payload = json.dumps({
            "service_id": details.service_id,
            "plan_id": details.plan_id
        })
        headers = {
            'Content-Type': 'application/json'
        }

        response = requests.request("PUT", template_engine_url + "/v1/template", headers=headers, data=payload)
        template_response = json.loads(response.text)  # Template response
        data["TemplateURL"] = template_response['TemplateURL']
        data["OnFailure"] = "DELETE"
        validator_response = self.stack.validate(template_response)

        return data

    @staticmethod
    def deprovision_details(instance_id):
        stack_name = instance_id
        return stack_name

    @staticmethod
    def update_details(instance_id, parameters):
        details = {"StackName": instance_id, "TemplateBody": json.dumps(parameters['TemplateBody'])}
        return details


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
        service_index += 1
        if service["id"] == service_id:
            for plan in service["plans"]:
                plan_index += 1
                if plan["id"] == plan_id:
                    imageurl = plan["metadata"]["imageurl"]
                    bindable = plan["metadata"]["bindable"]
                    planupdateable = plan["metadata"]["planupdateable"]

    return service_index, plan_index, bindable, planupdateable, imageurl
