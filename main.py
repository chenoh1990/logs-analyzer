from fastapi import FastAPI
import uvicorn
from app.api import users
from fastapi.middleware.cors import CORSMiddleware


# create application.
app = FastAPI(
    title='inventory microservice',
    description='A project designed to transfer information from a monolithic system to a microservices-based system.'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specify your frontend's URL like ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include relevant routers for application.
app.include_router(users.users)


if __name__ == '__main__':
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)
