"""Dependency injection container for Asubarnipal V2."""

from typing import Any, Callable, Optional, TypeVar, Generic, Type
from contextlib import contextmanager

T = TypeVar("T")


class Container:
    """
    Simple dependency injection container.
    
    Usage:
        container = Container()
        container.register(LLMRouter, scope="singleton")
        container.register(RAGEngine, scope="transient")
        
        router = container.resolve(LLMRouter)
    """

    def __init__(self) -> None:
        self._services: dict[type, dict[str, Any]] = {}
        self._singletons: dict[type, Any] = {}
        self._factories: dict[type, Callable] = {}

    def register(
        self,
        interface: type,
        implementation: Optional[type] = None,
        instance: Optional[Any] = None,
        factory: Optional[Callable] = None,
        scope: str = "transient",
    ) -> None:
        """
        Register a service.
        
        Args:
            interface: Type to register
            implementation: Concrete implementation class
            instance: Pre-created instance (for singleton)
            factory: Factory function to create instance
            scope: "singleton", "transient", or "scoped"
        """
        if instance is not None:
            self._singletons[interface] = instance
        elif factory is not None:
            self._factories[interface] = factory
        else:
            impl = implementation or interface
            self._services[interface] = {
                "implementation": impl,
                "scope": scope,
            }

    def resolve(self, interface: type[T]) -> T:
        """Resolve a service by type."""
        if interface in self._singletons:
            return self._singletons[interface]

        if interface in self._factories:
            return self._factories[interface]()

        if interface not in self._services:
            raise ValueError(f"No service registered for {interface}")

        service = self._services[interface]
        impl = service["implementation"]
        scope = service["scope"]

        if scope == "singleton":
            if interface not in self._singletons:
                self._singletons[interface] = impl()
            return self._singletons[interface]

        return impl()

    def resolve_all(self, interface: type[T]) -> list[T]:
        """Resolve all services for an interface."""
        results = []
        for registered_interface in self._services:
            if registered_interface == interface:
                results.append(self.resolve(registered_interface))
        return results

    def has(self, interface: type) -> bool:
        """Check if a service is registered."""
        return (
            interface in self._singletons
            or interface in self._factories
            or interface in self._services
        )

    def reset(self) -> None:
        """Reset all singletons (useful for testing)."""
        self._singletons.clear()

    @contextmanager
    def scoped(self):
        """Create a scoped context for request-level services."""
        old_singletons = self._singletons.copy()
        try:
            yield self
        finally:
            self._singletons = old_singletons


_global_container = Container()


def get_container() -> Container:
    """Get the global DI container."""
    return _global_container


def configure_services(container: Optional[Container] = None) -> Container:
    """Configure default services in the container."""
    if container is None:
        container = _global_container

    from core.llm_router import LLMRouter
    from core.cache import QueryCache
    from core.rate_limiter import CommandRateLimiter
    from core.circuit_breaker import CircuitBreakerRegistry
    from core.audit_logger import AuditLogger

    container.register(LLMRouter, scope="singleton")
    container.register(QueryCache, scope="singleton")
    container.register(CommandRateLimiter, scope="singleton")
    container.register(CircuitBreakerRegistry, scope="singleton")
    container.register(AuditLogger, scope="singleton")

    return container
