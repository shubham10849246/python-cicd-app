from fastapi import FastAPI
from .routes import router

app = FastAPI(title="Python CI/CD Demo App for Shubham", version="1.0.0")

@app.get("/health")
def health():
    return {"status": "UP"}

app.include_router(router)
