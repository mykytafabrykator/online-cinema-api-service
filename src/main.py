from fastapi import FastAPI

from routes import accounts, profiles, movies, genres, stars

app = FastAPI(
    title="Online Cinema API",
    description="An online cinema is a digital platform that allows users to "
                "select, watch, and purchase access to movies and other video "
                "materials via the internet. These services have become "
                "popular due to their convenience, a wide selection of "
                "content, and the ability to personalize the user experience.",
)

api_version_prefix = "/api/v1"

app.include_router(accounts.router, prefix="/users", tags=["Authentication"])
app.include_router(profiles.router, prefix="/profiles", tags=["Profile"])
app.include_router(movies.router, prefix="/movies", tags=["Movies"])
app.include_router(genres.router, prefix="/genres", tags=["Genres"])
app.include_router(stars.router, prefix="/stars", tags=["Stars"])


@app.get("/")
async def root():
    return {"message": "Documentation may be found on /docs"}
