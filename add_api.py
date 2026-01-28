from fastapi import FastAPI, HTTPException

app = FastAPI(title="add-api")


@app.post("/add")
async def add_numbers(payload: dict) -> dict:
    a = payload.get("a")
    b = payload.get("b")
    if a is None or b is None:
        raise HTTPException(status_code=400, detail="Missing 'a' or 'b'")
    try:
        result = float(a) + float(b)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="'a' and 'b' must be numbers")
    return {"result": result}
