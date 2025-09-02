import logging
from functools import partial

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

def get_model(config):
    class BrokerState(Model):
        class Meta:
            table_name = config.DYNAMODB_TABLE
            region = config.AWS_DEFAULT_REGION

        class IamUser(MapAttribute):
            access_key_id = UnicodeAttribute()
            #secret_access_key = EncryptedAttribute(key=config.ENCRYPTION_KEY)
            secret_access_key = UnicodeAttribute()

        instance_id = UnicodeAttribute(hash_key=True)
        context = JSONAttribute(default={})
        stack_status = UnicodeAttribute()
        service_id = UnicodeAttribute()
        plan_id = UnicodeAttribute()
        binding_ids = ListAttribute(default=[])
        state = UnicodeAttribute()
        stack_outputs = MapAttribute(default={})
        bind_status = UnicodeAttribute()
        update_status = UnicodeAttribute()
        user = UnicodeAttribute()
        plan_details = UnicodeAttribute()

        def __init__(self, *args, **kwargs):
            super(BrokerState, self).__init__(*args, **kwargs)

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
            return cls(*args, **filtered)

        @classmethod
        def init(cls):
            if cls.exists():
                return
            cls.create_table(read_capacity_units=5, write_capacity_units=5, wait=True)

    BrokerState.init()

    return BrokerState
