from alembic import context
from sqlalchemy import engine_from_config, pool

from backend.app.storage.models.base import Base

# Alembic CLI injects context.config at runtime.
# During pytest import, alembic.context does not have config.
config = getattr(context, "config", None)

target_metadata = Base.metadata


def run_migrations_offline():
    if config is None:
        return

    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    if config is None:
        return

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if config is not None:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()
