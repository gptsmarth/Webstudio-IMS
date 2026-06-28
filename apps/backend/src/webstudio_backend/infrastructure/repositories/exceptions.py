"""Repository-layer validation errors."""

from datetime import datetime


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


class InventoryItemArchiveNotAllowedError(RepositoryError):
    def __init__(self, inventory_item_id: str, reason: str) -> None:
        self.inventory_item_id = inventory_item_id
        self.reason = reason
        super().__init__(f"Inventory item {inventory_item_id} cannot be archived: {reason}")


class DuplicateUsernameError(RepositoryError):
    def __init__(self, username: str) -> None:
        self.username = username
        super().__init__(f"Username already exists: {username}")


class UserNotFoundError(RepositoryError):
    def __init__(self, user_id: int | str) -> None:
        self.user_id = user_id
        super().__init__(f"User not found: {user_id}")


class LastMainAdminError(RepositoryError):
    def __init__(self) -> None:
        super().__init__("Cannot modify the last active Main Admin account")


class SelfMainAdminDisableError(RepositoryError):
    def __init__(self) -> None:
        super().__init__("Cannot disable your own Main Administrator account")


class SystemAlreadyInitializedError(RepositoryError):
    def __init__(self) -> None:
        super().__init__("System is already initialized")


class SystemNotInitializedError(RepositoryError):
    def __init__(self) -> None:
        super().__init__("System is not initialized")


class InvalidCredentialsError(RepositoryError):
    def __init__(self) -> None:
        super().__init__("Invalid username or password")


class AccountLockedError(RepositoryError):
    def __init__(self, locked_until: datetime | None = None) -> None:
        self.locked_until = locked_until
        super().__init__("Account is temporarily locked")


class AccountDisabledError(RepositoryError):
    def __init__(self) -> None:
        super().__init__("Account is disabled")


class InvalidRefreshTokenError(RepositoryError):
    def __init__(self) -> None:
        super().__init__("Invalid or expired refresh token")


class RefreshTokenReuseError(RepositoryError):
    def __init__(self) -> None:
        super().__init__("Refresh token reuse detected")


class SetupPendingRecoveryConfirmationError(RepositoryError):
    def __init__(self) -> None:
        super().__init__("Setup is awaiting recovery key confirmation")


class InvalidRecoveryKeyError(RepositoryError):
    def __init__(self) -> None:
        super().__init__("Invalid recovery key")


class MainAdminNotFoundError(RepositoryError):
    def __init__(self) -> None:
        super().__init__("Main Admin account not found")


class NotificationNotFoundError(RepositoryError):
    def __init__(self, notification_id: int) -> None:
        self.notification_id = notification_id
        super().__init__(f"Notification not found: {notification_id}")


class NotificationAlreadyResolvedError(RepositoryError):
    def __init__(self, notification_id: int) -> None:
        self.notification_id = notification_id
        super().__init__(f"Notification is already resolved: {notification_id}")


class NotificationResolveNotAllowedError(RepositoryError):
    def __init__(self) -> None:
        super().__init__("Insufficient permission to resolve notifications")


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


class ArchivedInventoryOperationError(RepositoryError):
    def __init__(self, inventory_item_id: str, operation: str) -> None:
        self.inventory_item_id = inventory_item_id
        self.operation = operation
        super().__init__(f"Archived inventory item cannot be {operation}: {inventory_item_id}")


class InventoryNotAvailableForSaleError(RepositoryError):
    def __init__(self, inventory_item_id: str, status: str) -> None:
        self.inventory_item_id = inventory_item_id
        self.status = status
        super().__init__(
            f"Inventory item {inventory_item_id} is not available for sale (status: {status})",
        )


class InventoryAlreadySoldError(RepositoryError):
    def __init__(self, inventory_item_id: str) -> None:
        self.inventory_item_id = inventory_item_id
        super().__init__(f"Inventory item is already sold: {inventory_item_id}")


class UseLocationTransferEndpointError(RepositoryError):
    def __init__(self) -> None:
        super().__init__("Use PATCH /api/v1/inventory/{id}/location to transfer location")


class SourceLocationMismatchError(RepositoryError):
    def __init__(self, inventory_item_id: str, from_location_id: int) -> None:
        self.inventory_item_id = inventory_item_id
        self.from_location_id = from_location_id
        super().__init__(
            "Source location "
            f"{from_location_id} does not match inventory item {inventory_item_id} "
            "current location",
        )
