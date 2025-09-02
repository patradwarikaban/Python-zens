import logging

from boto3.session import Session
from cachetools import TTLCache, cached

LOG = logging.getLogger(__name__)

SIMPLE_TRUST_POLICY = """
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ec2.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}""".strip()

retry_config = dict(tries=7, delay=1, backoff=1.5, max_delay=30)


class CloudFormationStack:
    arn_key = None
    events_namespace = None
    identifier_key = None
    resource_type = None
    resource_key = None

    def __init__(self, **kwargs):
        session = Session()
        self.region_name = kwargs["region_name"]
        self.client = session.client("cloudformation", region_name=self.region_name)

    def create(self, kwargs):
        return self.client.create_stack(**kwargs)

    def validate(self, kwargs):
        return self.client.validate_template(**kwargs)

    def describe(self, kwargs):
        return self._cached_describe(kwargs)

    def list_deleted_stacks(self):
        return self._cached_list_deleted_stacks()
    
    def update(self, **kwargs):
        return self.client.update_stack(**kwargs)

    def delete(self, **kwargs):
        return self.client.delete_stack(**kwargs)

    @cached(cache=TTLCache(maxsize=1024, ttl=1))
    def _cached_describe(self, stack_id):
        response = self.client.describe_stacks(StackName=stack_id)
        return response[self.resource_key][0]

    @cached(cache=TTLCache(maxsize=1024, ttl=1))
    def _cached_list_deleted_stacks(self):
        return self.client.list_stacks(
          StackStatusFilter=[
            'DELETE_COMPLETE'
          ]
        )