"""Drop all tables from the database.

Run from the Bed/ directory:  python -m src.drop_tables
"""

from .database import Base, engine


def drop_all_tables() -> None:
    # This import is crucial. It registers all the models with `Base.metadata`
    # so that `drop_all` knows which tables to drop.
    from . import models  # noqa: F401

    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("All tables dropped.")

if __name__ == "__main__":
    drop_all_tables()