# 🎬 Online Cinema API Service

This project is a **FastAPI-based REST API** service for an online cinema platform, 
providing user authentication, movie management, order processing, payment integration, and more. 
The service is containerized using **Docker** and orchestrated with **Docker Compose**.

## 🛠 Installation

### `Python3` & `Docker` must be already installed

### Clone the Repository
```shell
git clone https://github.com/mykytafabrykator/online-cinema-api-service.git
cd online-cinema-api-service
```
### Configure Environment Variables
```shell
cp .env.sample .env
```
### Run the Project with Docker
```shell
docker-compose -f docker-compose-dev.yml up --build
```
### This will start all required services:
 - **PostgreSQL (Database)**
 - **FastAPI Backend**
 - **Alembic Migration Service**
 - **Redis (Task Queue Backend for Celery)**
 - **Celery Worker & Celery Beat**
 - **MinIO (Object Storage)**
 - **Mailhog (Email Testing Tool)**
 - **PGAdmin (Database Administration Panel)**

## 📄 API Documentation
### After running the project, the API documentation will be available at:
* **Swagger UI**: http://127.0.0.1:8000/docs/

## ✨ Features
- User Authentication & Authorization (JWT-based)
- Movie Management (Genres, Directors, Actors, Ratings, Favorites, Likes)
- Shopping Cart & Order Processing
- Stripe Payment Integration (Checkout, Payment History)
- Celery Task Queue & Redis for background tasks
- MinIO for object storage (media files)
- PGAdmin for database administration
- Swagger API Documentation
- Dockerized for Easy Deployment

## ✍️ Tech Stack
- Python 3.12
- FastAPI
- SQLAlchemy & Alembic (Database ORM & Migrations)
- PostgreSQL (Database)
- Redis & Celery (Task Queue for Background Processing)
- Stripe API (Payment Processing)
- MinIO (Object Storage for Media Files)
- Mailhog (Email Testing Tool)
- Poetry (Project dependencies)
- Docker & Docker Compose (Containerization & Deployment)
- JWT Authentication
- CI Pipeline