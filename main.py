from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}


if __name__ == "__main__":
    """
    Run the app with:
    uvicorn main:app --reload --host 127.0.0.1 --port 8081
    """
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8081)
