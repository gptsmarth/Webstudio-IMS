"""Entity repositories."""

from webstudio_backend.infrastructure.repositories.brand_repository import BrandRepository
from webstudio_backend.infrastructure.repositories.exceptions import (
    DuplicateModelNumberError,
    DuplicateNameError,
    DuplicateSerialNumberError,
    InactiveLocationError,
    InactiveProductModelError,
    InvalidFieldValueError,
    InventoryItemDeleteNotAllowedError,
    ProductModelHasHistoryError,
    RepositoryError,
    RequiredFieldError,
)
from webstudio_backend.infrastructure.repositories.inventory_item_repository import (
    InventoryItemRepository,
)
from webstudio_backend.infrastructure.repositories.location_repository import LocationRepository
from webstudio_backend.infrastructure.repositories.product_model_repository import (
    ProductModelRepository,
)

__all__ = [
    "BrandRepository",
    "DuplicateModelNumberError",
    "DuplicateNameError",
    "DuplicateSerialNumberError",
    "InactiveLocationError",
    "InactiveProductModelError",
    "InvalidFieldValueError",
    "InventoryItemDeleteNotAllowedError",
    "InventoryItemRepository",
    "LocationRepository",
    "ProductModelHasHistoryError",
    "ProductModelRepository",
    "RepositoryError",
    "RequiredFieldError",
]
