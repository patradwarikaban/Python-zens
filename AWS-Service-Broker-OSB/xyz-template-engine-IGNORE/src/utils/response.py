from typing import List

from src.catalog.model.catalog_model import Catalog


class EmptyResponse:
    pass


class ErrorResponse:
    def __init__(self, error: str = None, description: str = None):
        self.error = error
        self.description = description


class CatalogResponse:
    def __init__(self, catalogs: List[Catalog]):
        self.catalogs = catalogs
