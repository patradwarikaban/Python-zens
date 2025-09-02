import logging
import warnings
from http import HTTPStatus
import json
from json.decoder import JSONDecodeError
import configparser
import os
from flask import Blueprint
from flask import request

from src.catalog import catalogs
from src.template.load import TemplateHelper
from src.te_utils import constants, errors
from src.te_utils.helpers import to_json_response, ensure_list
from src.te_utils.request_filter import print_request, check_version, check_originating_identity, requires_application_json
from src.te_utils.response import ErrorResponse, CatalogResponse, EmptyResponse
from src.te_utils.settings import DISABLE_VERSION_CHECK, MIN_VERSION

logger = logging.getLogger(__name__)


class TemplateEngine:

    def __init__(self):
        pass

    def get_blueprint(
            self,
            logger: logging.Logger
    ) -> Blueprint:
        """
        Returns the blueprint with template engine api.
        :param logger: Used for api logs. This will not influence Flasks logging behavior.
        :return: Blueprint to register with Flask app instance
        """
        template_engine = Blueprint("template_engine", __name__)

        # Apply filters
        logger.debug("Apply print_request filter for debugging")
        template_engine.before_request(print_request)

        if DISABLE_VERSION_CHECK:
            logger.warning(
                "Minimum API version is not checked, "
                "this can cause illegal contracts between service broker and platform!"
            )
        else:
            logger.debug("Apply check_version filter for version %s" % str(MIN_VERSION))
            template_engine.before_request(check_version)

        logger.debug("Apply check_originating_identity filter")
        template_engine.before_request(check_originating_identity)

        @template_engine.errorhandler(Exception)
        def error_handler(e):
            logger.exception(e)
            return (
                to_json_response(
                    ErrorResponse(description=constants.DEFAULT_EXCEPTION_ERROR_MESSAGE)
                ),
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

        @template_engine.errorhandler(NotImplementedError)
        def error_handler_not_implemented(e):
            logger.exception(e)
            return (
                to_json_response(
                    ErrorResponse(
                        description=constants.DEFAULT_NOT_IMPLEMENTED_ERROR_MESSAGE
                    )
                ),
                HTTPStatus.NOT_IMPLEMENTED,
            )

        @template_engine.errorhandler(errors.ErrBadRequest)
        def error_handler_bad_request(e):
            logger.exception(e)
            return (
                to_json_response(
                    ErrorResponse(description=constants.DEFAULT_BAD_REQUEST_ERROR_MESSAGE)
                ),
                HTTPStatus.BAD_REQUEST,
            )

        @template_engine.route("/v1/catalog", methods=["GET"])
        def catalog():
            """
            :return: Catalog of broker (List of services)
            """
            try:
                catalog_list = ensure_list(catalogs)

                if catalog_list is None:
                    warnings.warn("Catalog resource file not found!!!")
                    raise errors.ServiceException("Catalog resource file not found!!!")

                return to_json_response(CatalogResponse(list(catalog_list)))

            except errors.ServiceException as e:
                logger.exception(e)
                return to_json_response(EmptyResponse()), HTTPStatus.INTERNAL_SERVER_ERROR

        @template_engine.route("/v1/template/<template_name>", methods=["GET"])
        def fetch_template(template_name):
            try:
                template = TemplateHelper.load_template(template_name)
                return to_json_response(template), HTTPStatus.OK
            except (TypeError, KeyError, JSONDecodeError) as e:
                logger.exception(e)
                return (
                    to_json_response(ErrorResponse(description=str(e))),
                    HTTPStatus.BAD_REQUEST,
                )

            except Exception as e:
                logger.exception(e)
                return (
                    to_json_response(ErrorResponse(description=str(e))),
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )

        @template_engine.route("/v1/template", methods=["PUT"])
        @requires_application_json
        def create_template():
            try:
                template_json = request.get_json(silent=True)
                service_id = template_json['service_id']
                plan_id = template_json['plan_id']
                aws_broker_dir = get_env()
                broker_config = aws_broker_dir + '/' + 'config/broker.config'
                catalog_file = get_config_values(broker_config, 'FILE_DETAILS', 'catalog_file')
                service_index, plan_index, bindable, planupdateable, imageurl = get_Plandetails(service_id, plan_id,
                                                                                                catalog_file)

                return to_json_response({"TemplateURL": imageurl}), HTTPStatus.ACCEPTED

            except (TypeError, KeyError, JSONDecodeError) as e:
                logger.exception(e)
                return (
                    to_json_response(ErrorResponse(description=str(e))),
                    HTTPStatus.BAD_REQUEST,
                )

            except Exception as e:
                logger.exception(e)
                return (
                    to_json_response(ErrorResponse(description=str(e))),
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )

        return template_engine

    def serve(
            self,
            logger: logging.Logger = logging.root,
            host="0.0.0.0",
            port=5000,
            debug=False,
    ):
        """
        Starts flask with the given templates.
        :param logger: Used for api logs. This will not influence Flasks logging behavior
        :param host: Host, defaults to all interfaces (0.0.0.0)
        :param port: Port
        :param debug: Enables debugging in flask app
        """

        from flask import Flask

        app = Flask(__name__)
        app.debug = debug

        blueprint = self.get_blueprint(logger=logger)

        logger.debug("Register template engine")
        app.register_blueprint(blueprint)

        try:
            from gevent.pywsgi import WSGIServer

            logger.info(f"Start Gevent server on {host}:{port}")
            http_server = WSGIServer((host, port), app)
            http_server.serve_forever()
        except ImportError:

            logger.info(f"Start Flask on {host}:{port}")
            logger.warning("Use a server like gevent or gunicorn for production!")
            app.run(host, port)


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
