"""
Context management for FinCLI

Handles session-based context filtering using configuration file.
"""

from typing import List, Optional

from .config import Config


class ContextManager:
    """Manages task contexts using configuration file."""

    CONFIG_KEY = "current_context"
    DEFAULT_CONTEXT = "default"

    @classmethod
    def set_context(cls, context_name: str) -> None:
        """Set the current context for the session.

        Args:
            context_name: Name of the context to set
        """
        if not cls._is_valid_context_name(context_name):
            raise ValueError(f"Invalid context name: {context_name}")

        config = Config()
        config.set(cls.CONFIG_KEY, context_name)

    @classmethod
    def get_current_context(cls) -> str:
        """Get the current context from configuration.

        Returns:
            Current context name, defaults to 'default'
        """
        config = Config()
        return config.get(cls.CONFIG_KEY, cls.DEFAULT_CONTEXT)

    @classmethod
    def clear_context(cls) -> None:
        """Clear the current context, reverting to default."""
        config = Config()
        config.set(cls.CONFIG_KEY, cls.DEFAULT_CONTEXT)

    @classmethod
    def list_contexts(cls, db_manager) -> List[str]:
        """List all available contexts from existing tasks.

        Args:
            db_manager: Database manager instance

        Returns:
            List of context names
        """
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()

            # Get unique contexts from tasks table
            cursor.execute("SELECT DISTINCT context FROM tasks WHERE context IS NOT NULL ORDER BY context")
            contexts = [row[0] for row in cursor.fetchall()]

            # Always include default context
            if cls.DEFAULT_CONTEXT not in contexts:
                contexts.insert(0, cls.DEFAULT_CONTEXT)

            return contexts

    @classmethod
    def _is_valid_context_name(cls, context_name: str) -> bool:
        """Validate context name format.

        Args:
            context_name: Name to validate

        Returns:
            True if valid, False otherwise
        """
        if not context_name or not context_name.strip():
            return False

        # Reserved words that can't be used as contexts
        reserved_words = {"and", "or", "ref", "due", "recur", "depends", "not", "context"}

        normalized_name = context_name.lower().strip()
        if normalized_name in reserved_words:
            return False

        # Must be alphanumeric with underscores/hyphens
        if not normalized_name.replace("_", "").replace("-", "").isalnum():
            return False

        return True
