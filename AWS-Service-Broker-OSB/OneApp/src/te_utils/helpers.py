import json
from typing import Union, Iterable, Any
from flask import jsonify
from src.te_utils.response import CatalogResponse


def _to_dict(obj):
    if isinstance(obj, dict):
        data = {}
        for (k, v) in obj.items():
            data[k] = _to_dict(v)
        return data
    if isinstance(obj, CatalogResponse):
        data = []
        for obj_data in obj.catalogs:
            data.append(obj_data.__dict__)
        return data
    elif hasattr(obj, "__dict__"):
        return obj.__dict__
    elif hasattr(obj, "__iter__") and not isinstance(obj, str):
        return [_to_dict(v) for v in obj]
    else:
        return obj


def version_tuple(v):
    return tuple(map(int, (v.split("."))))


def ensure_list(x: Union[Iterable, Any]):
    import collections

    if isinstance(x, collections.abc.Iterable):
        return x
    else:
        return [x]


def to_json_response(obj):
    return jsonify(_to_dict(obj))