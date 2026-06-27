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


class DuplicateModelNumberError(RepositoryError):
    def __init__(self, brand_id: int, model_number: str) -> None:
        self.brand_id = brand_id
        self.model_number = model_number
        super().__init__(
            f"Model number already exists for brand {brand_id}: {model_number}",
        )


class InvalidFieldValueError(RepositoryError):
    def __init__(self, field: str, message: str) -> None:
        self.field = field
        super().__init__(f"{field}: {message}")


class ProductModelHasHistoryError(RepositoryError):
    def __init__(self, product_model_id: str) -> None:
        self.product_model_id = product_model_id
        super().__init__(
            "Product model "
            f"{product_model_id} cannot be deleted because historical references exist",
        )
