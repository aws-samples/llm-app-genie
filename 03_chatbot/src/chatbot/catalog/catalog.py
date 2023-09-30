""" Module for catalogs that contain base items. """
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, TypeVar

from .catalog_item import CatalogItem

T = TypeVar("T", bound=CatalogItem)

FRIENDLY_NAME_TAG = "genie:friendly-name"


@dataclass
class Catalog(ABC, List[T]):
    """Base class for catalogs."""

    regions: List[str]
    """ List of regions where the catalog looks for resources. """

    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def bootstrap(self) -> None:
        """
        Bootstraps the catalog.
        """

    def get_friendly_names(self) -> List[str]:
        """A friendly name is a human readable name that can be used in to represent an item.

        Returns:
          A list of friendly names for the catalog
        """
        return [item.friendly_name for item in self]


@dataclass
class CatalogById(ABC, Dict[str, T]):
    """Base class for catalogs that store catalog items by id."""

    def __getitem__(self, __key: str) -> T:
        item = super().get(__key, None)
        if item is None:
            item = self._retrieve(__key)
            self[__key] = item
        return item

    @abstractmethod
    def _retrieve(self, key: str) -> T:
        """Retrieves an item that does not exist in the catalog."""
