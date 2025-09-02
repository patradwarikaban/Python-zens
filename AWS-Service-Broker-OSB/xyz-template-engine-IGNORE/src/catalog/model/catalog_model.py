from typing import Optional


class CatalogMetadata:
    def __init__(
        self,
        displayName: str,
        imageUrl: str,
        longDescription: str,
        providerDisplayName: str,
        documentationUrl: str,
        supportUrl: str,
        shareable: Optional[bool] = None
    ):
        self.displayName = displayName
        self.imageUrl = imageUrl
        self.longDescription = longDescription
        self.providerDisplayName = providerDisplayName
        self.documentationUrl = documentationUrl
        self.supportUrl = supportUrl
        self.shareable = shareable

        # self.__dict__.update(kwargs)


class Catalog(object):
    def __init__(
            self,
            kwargs
    ):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.__dict__.update(kwargs)

    # def __init__(
    #     self,
    #     id: str,
    #     name: str,
    #     template_name: str,
    #     description: str,
    #     metadata: CatalogMetadata = None,
    #     bindable: bool = None,
    # ):
    #     self.id = id
    #     self.name = name
    #     self.template_name = template_name
    #     self.description = description
    #     self.metadata = metadata
    #     self.bindable = bindable
    #
    #     # self.__dict__.update(kwargs)
