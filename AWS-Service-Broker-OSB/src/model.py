import logging
from functools import partial
import os

from pynamodb.attributes import (
    JSONAttribute,
    ListAttribute,
    MapAttribute,
    UnicodeAttribute,

)
from pynamodb.exceptions import DoesNotExist
from pynamodb.models import Model


'''class EncryptedAttribute(UnicodeAttribute):
    def __init__(self, key, *args, **kwargs):
        super(EncryptedAttribute, self).__init__(*args, **kwargs)
        self.encryption_key = key

    def serialize(self, value):
        encrypted_value = utils.encrypt_data(value, key=self.encryption_key)
        return super(EncryptedAttribute, self).serialize(encrypted_value)

    def deserialize(self, value):
        decrypted_value = utils.decrypt_data(value, key=self.encryption_key)
        return super(EncryptedAttribute, self).deserialize(decrypted_value)
'''

# def get_model(config):


class get_model(Model):
    class Meta:
        os.environ["AWS_PROFILE"] = os.getenv("AWS_USER_PROFILE") 
        table_name = "service-broker-ops-state"
        region = "us-east-1"


    instance_id = UnicodeAttribute(hash_key=True)
    context = JSONAttribute(default=0)
    stack_status = UnicodeAttribute()
    service_id = UnicodeAttribute()
    plan_id = UnicodeAttribute()
    binding_ids = ListAttribute(default=0)
    state = UnicodeAttribute()
    stack_outputs = ListAttribute(default=0)
    bind_status = UnicodeAttribute()
    update_status = UnicodeAttribute()
    user = UnicodeAttribute()
    plan_details = UnicodeAttribute()

    @classmethod
    def init(cls):
        if cls.exists():
            return
        cls.create_table(read_capacity_units=5, write_capacity_units=5, wait=True)

"""
    def __init__(self, *args, **kwargs):
        super(BrokerState, self).__init__(*args, **kwargs)
        #super(BrokerState, self).__init__(*args)


    @classmethod
    def get(cls, hash_key, range_key=None, consistent_read=False):
        try:
            record = super(BrokerState, cls).get(
                hash_key, range_key, consistent_read
            )
        except DoesNotExist:
            record = None
        return record

    @classmethod
    def create_record(cls, *args, **kwargs):
        allowed_attrs = (
            "context",
            "stack_status",
            "service_id",
            "plan_id",
            "instance_id",
            "stack_outputs",
            "state",
            "bind_status",
            "update_status",
            "user",
            "plan_details"
        )
        filtered = {k: v for k, v in kwargs.items() if k in allowed_attrs}

        print(filtered)
        return cls(*args, **filtered)

    @classmethod
    def init(cls):
        if cls.exists():
            return
        cls.create_table(read_capacity_units=5, write_capacity_units=5, wait=True)

BrokerState.init()

return BrokerState
"""

