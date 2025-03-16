import os

from database.models.base import Base
from database.models.accounts import (
    ActivationToken,
    PasswordResetToken,
    RefreshToken,
    User,
    UserGroup,
    UserGroupEnum,
    UserProfile,
    GenderEnum,
)
from database.models.movies import (
    Certification,
    Director,
    Genre,
    Movie,
    MovieDirectors,
    MovieGenres,
    MovieStars,
    Star,
    FavoriteMovie,
    MovieLike
)
from database.models.payments import Payment, PaymentItem, PaymentStatusEnum
from database.models.orders import Order, OrderItem
from database.models.shopping_cart import Cart, CartItem

environment = os.getenv("ENVIRONMENT", "developing")

if environment == "testing":
    from database.session_sqlite import (
        get_sqlite_db_contextmanager as get_db_contextmanager,
        get_sqlite_db as get_db
    )
else:
    from database.session_postgresql import (
        get_postgresql_db_contextmanager as get_db_contextmanager,
        get_postgresql_db as get_db
    )
