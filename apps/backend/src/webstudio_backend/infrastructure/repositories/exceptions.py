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


class DuplicateSerialNumberError(RepositoryError):
    def __init__(self, serial_number: str) -> None:
        self.serial_number = serial_number
        super().__init__(f"Serial number already exists: {serial_number}")


class InactiveProductModelError(RepositoryError):
    def __init__(self, product_model_id: str) -> None:
        self.product_model_id = product_model_id
        super().__init__(f"Product model {product_model_id} is not active")


class InactiveLocationError(RepositoryError):
    def __init__(self, location_id: int) -> None:
        self.location_id = location_id
        super().__init__(f"Location {location_id} is not active")


class InventoryItemDeleteNotAllowedError(RepositoryError):
    def __init__(self, inventory_item_id: str, reason: str) -> None:
        self.inventory_item_id = inventory_item_id
        self.reason = reason
        super().__init__(f"Inventory item {inventory_item_id} cannot be deleted: {reason}")


class InventoryItemNotFoundError(RepositoryError):
    def __init__(self, inventory_item_id: str) -> None:
        self.inventory_item_id = inventory_item_id
        super().__init__(f"Inventory item not found: {inventory_item_id}")


class LocationNotFoundError(RepositoryError):
    def __init__(self, location_id: int) -> None:
        self.location_id = location_id
        super().__init__(f"Location not found: {location_id}")


class SameLocationMovementError(RepositoryError):
    def __init__(self) -> None:
        super().__init__("Source and destination locations must differ")


class SoldItemCannotMoveError(RepositoryError):
    def __init__(self, inventory_item_id: str) -> None:
        self.inventory_item_id = inventory_item_id
        super().__init__(f"Sold inventory item cannot be moved: {inventory_item_id}")


class SourceLocationMismatchError(RepositoryError):
    def __init__(self, inventory_item_id: str, from_location_id: int) -> None:
        self.inventory_item_id = inventory_item_id
        self.from_location_id = from_location_id
        super().__init__(
            "Source location "
            f"{from_location_id} does not match inventory item {inventory_item_id} "
            "current location",
        )
