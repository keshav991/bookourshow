from fastapi import FastAPI

app = FastAPI(
    title="Movie Booking API",
    description="Backend for movie ticket booking",
    version="1.0.0"
)

@app.get("/")
def home():
    return {"message": "Movie Booking API is running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}