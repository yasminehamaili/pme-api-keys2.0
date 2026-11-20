from fastapi import Depends
from ratelimit import enforce_limits


@app.get("/v1/ping")
async def ping(auth=Depends(enforce_limits)):
    return {"ok": True, "customer_id": auth["customer_id"]}