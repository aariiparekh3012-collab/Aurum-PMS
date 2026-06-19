"""Alembic environment — uses app settings + ORM metadata for autogenerate."""
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.core.database import Base

# Import ALL model files so their tables register on Base.metadata
from app.infrastructure.db import models  # noqa: F401  (onboarding / public)
from app.infrastructure.db import models_client  # noqa: F401
from app.infrastructure.db import models_reference  # noqa: F401
from app.infrastructure.db import models_trading  # noqa: F401
from app.infrastructure.db import models_portfolio  # noqa: F401
from app.infrastructure.db import models_performance  # noqa: F401
from app.infrastructure.db import models_notifications  # noqa: F401
from app.infrastructure.db import models_auth  # noqa: F401
from app.infrastructure.db import models_nse_reports  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata


def include_object(object_, name, type_, reflected, compare_to):
    """Allow autogenerate to see tables in all schemas."""
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        include_schemas=True,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_schemas=True,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
