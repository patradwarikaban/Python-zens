import logging
import os
import uuid


class Config:
    DEBUG = False
    TESTING = False
    AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "01234567890123456789012345678901")
    APP_NAME = "Service Broker"

    @property
    def aws_config(self):
        return {
            "aws_access_key_id": self.AWS_ACCESS_KEY_ID,
            "aws_secret_access_key": self.AWS_SECRET_ACCESS_KEY,
            "region_name": self.AWS_DEFAULT_REGION,
        }

    DYNAMODB_TABLE = "service-broker-ops-state"


class DevConfig(Config):
    DEBUG = True
    BROKER_USE_SSL = False


class ProdConfig(Config):
    DEBUG = False



