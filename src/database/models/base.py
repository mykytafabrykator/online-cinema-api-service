from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all database models.

    This class provides a common structure for SQLAlchemy ORM models.
    """

    @classmethod
    def default_order_by(cls) -> None:
        """
        Define the default order by behavior for models.

        This method is intended to be overridden in child classes
        to specify a default ordering when retrieving records.

        :return: None (override in child models if needed)
        """
        return None
