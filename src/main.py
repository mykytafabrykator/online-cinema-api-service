from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import (
    accounts,
    profiles,
    movies,
    genres,
    stars,
    shopping_cart,
    orders,
    payments,
)

app = FastAPI(
    title="Online Cinema API",
    description="An online cinema is a digital platform that allows users to "
                "select, watch, and purchase access to movies and other video "
                "materials via the internet. These services have become "
                "popular due to their convenience, a wide selection of "
                "content, and the ability to personalize the user experience.",
)

api_version_prefix = "/api/v1"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    accounts.router,
    prefix=f"{api_version_prefix}/users",
    tags=["Authentication"]
)
app.include_router(
    profiles.router,
    prefix=f"{api_version_prefix}/profiles",
    tags=["Profile"]
)
app.include_router(
    movies.router,
    prefix=f"{api_version_prefix}/movies",
    tags=["Movies"]
)
app.include_router(
    genres.router,
    prefix=f"{api_version_prefix}/genres",
    tags=["Genres"]
)
app.include_router(
    stars.router,
    prefix=f"{api_version_prefix}/stars",
    tags=["Stars"]
)
app.include_router(
    shopping_cart.router,
    prefix=f"{api_version_prefix}/shopping-cart",
    tags=["Shopping Cart"]
)
app.include_router(
    orders.router,
    prefix=f"{api_version_prefix}/orders",
    tags=["Orders"]
)
app.include_router(
    payments.router,
    prefix=f"{api_version_prefix}/payments",
    tags=["Payments"]
)


@app.get("/")
async def root():
    return {"message": "Documentation may be found on /docs"}
