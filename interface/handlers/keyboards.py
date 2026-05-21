"""Inline keyboard builders for Telegram commands."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_charlar_keyboard() -> InlineKeyboardMarkup:
    """Build inline keyboard for /charlar modes."""
    keyboard = [
        [
            InlineKeyboardButton("Libre", callback_data="charlar:libre"),
            InlineKeyboardButton("Consultor", callback_data="charlar:consultor"),
        ],
        [
            InlineKeyboardButton("Devil", callback_data="charlar:devil"),
            InlineKeyboardButton("Socratico", callback_data="charlar:socratico"),
        ],
        [
            InlineKeyboardButton("Lateral", callback_data="charlar:lateral"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_model_keyboard() -> InlineKeyboardMarkup:
    """Build inline keyboard for /model selection."""
    keyboard = [
        [
            InlineKeyboardButton("Ollama", callback_data="model:ollama"),
            InlineKeyboardButton("Gemini", callback_data="model:gemini"),
        ],
        [
            InlineKeyboardButton("Auto", callback_data="model:auto"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_vault_keyboard() -> InlineKeyboardMarkup:
    """Build inline keyboard for vault operations."""
    keyboard = [
        [
            InlineKeyboardButton("Listar", callback_data="vault:list"),
            InlineKeyboardButton("Info", callback_data="vault:info"),
        ],
        [
            InlineKeyboardButton("Crear", callback_data="vault:create"),
            InlineKeyboardButton("Cambiar", callback_data="vault:switch"),
        ],
        [
            InlineKeyboardButton("Exportar", callback_data="vault:export"),
            InlineKeyboardButton("Importar", callback_data="vault:import"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_query_mode_keyboard() -> InlineKeyboardMarkup:
    """Build inline keyboard for query modes."""
    keyboard = [
        [
            InlineKeyboardButton("Wiki", callback_data="query:wiki"),
            InlineKeyboardButton("Vectorial", callback_data="query:vectorial"),
        ],
        [
            InlineKeyboardButton("Hibrido", callback_data="query:hybrid"),
            InlineKeyboardButton("H-Mem", callback_data="query:hmem"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_yes_no_keyboard(yes_data: str = "yes", no_data: str = "no") -> InlineKeyboardMarkup:
    """Build simple yes/no keyboard."""
    keyboard = [
        [
            InlineKeyboardButton("Si", callback_data=yes_data),
            InlineKeyboardButton("No", callback_data=no_data),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_back_keyboard(back_data: str = "back") -> InlineKeyboardMarkup:
    """Build keyboard with back button."""
    keyboard = [
        [InlineKeyboardButton("Volver", callback_data=back_data)],
    ]
    return InlineKeyboardMarkup(keyboard)
