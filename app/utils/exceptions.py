class ImportException(Exception):
    pass


class ConfigurationException(ImportException):
    pass


class ValidationException(ImportException):
    pass


class StorageException(ImportException):
    pass
