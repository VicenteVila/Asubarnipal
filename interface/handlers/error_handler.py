"""Centralized error handling decorator for Telegram handlers."""

import functools
import logging
from typing import Any, Callable, TypeVar

from telegram import Update
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def handle_errors(fallback_msg: str = "An error occurred. Please try again later.") -> Callable[[F], F]:
    """Decorator to wrap Telegram handlers with error handling.

    Catches exceptions, logs them, and sends a user-friendly message.

    Args:
        fallback_msg: Default message to show on error.

    Usage:
        @handle_errors()
        async def my_handler(update: Update, context: CallbackContext) -> None:
            ...

        @handle_errors("Custom error message")
        async def another_handler(update: Update, context: CallbackContext) -> None:
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(update: Update, context: CallbackContext, *args: Any, **kwargs: Any) -> Any:
            try:
                return await func(update, context, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
                if update.effective_message:
                    await update.effective_message.reply_text(fallback_msg)
                raise

        return wrapper  # type: ignore[return-value]

    return decorator


def handle_errors_silent(fallback_msg: str = "An error occurred.") -> Callable[[F], F]:
    """Decorator that catches and logs errors without re-raising.

    Use for background tasks where you don't want to crash the handler chain.

    Args:
        fallback_msg: Message to show on error.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(update: Update, context: CallbackContext, *args: Any, **kwargs: Any) -> Any:
            try:
                return await func(update, context, *args, **kwargs)
            except Exception as e:
                logger.error(f"Silent error in {func.__name__}: {e}", exc_info=True)
                if update.effective_message:
                    await update.effective_message.reply_text(fallback_msg)

        return wrapper  # type: ignore[return-value]

    return decorator
