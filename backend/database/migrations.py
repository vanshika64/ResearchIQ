"""Small, non-destructive schema upgrades for existing local databases."""

from sqlalchemy import inspect, text


def migrate_schema(engine) -> None:
    """Bring legacy tables up to the current model schema.

    ``create_all`` creates missing tables, but intentionally does not alter
    existing ones. Older ResearchIQ databases therefore need this migration
    before uploads start inserting page-aware chunks.
    """
    inspector = inspect(engine)
    if "paper_chunks" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("paper_chunks")}
    if "page_number" not in columns:
        # Existing chunks have no page metadata; use page 1 as a legacy default.
        # New uploads store their actual page numbers.
        with engine.begin() as connection:
            connection.execute(text(
                "ALTER TABLE paper_chunks "
                "ADD COLUMN page_number INTEGER NOT NULL DEFAULT 1"
            ))
