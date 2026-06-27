"""Repository-layer validation errors."""


class RepositoryError(Exception):
    """Base class for repository validation failures."""


class RequiredFieldError(RepositoryError):
    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(f"{field} is required")


class DuplicateNameError(RepositoryError):
    def __init__(self, entity: str, name: str) -> None:
        self.entity = entity
        self.name = name
        super().__init__(f"{entity} name already exists: {name}")
