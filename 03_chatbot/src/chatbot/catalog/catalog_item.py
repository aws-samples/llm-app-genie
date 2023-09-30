""" Abstract base class that represents a catalog item. """

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class CatalogItem(ABC, Generic[T]):
    """Abstract base class that represents a catalog item."""

    friendly_name: str

    @abstractmethod
    def get_instance(self) -> T:
        """Returns an instance of the item."""

    def __str__(self):
        return self.friendly_name
