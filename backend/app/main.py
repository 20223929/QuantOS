from fastapi import FastAPI

app = FastAPI(title="QuantOS Next API")


@app.get("/")
async def root():
    return {"name": "QuantOS Next", "version": "0.1.0"}
