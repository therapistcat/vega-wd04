import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import json
from bson import json_util

async def inspect_events():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["vega_hackathon"]
    cursor = db["vapi_events"].find().sort("_id", -1).limit(5)
    events = await cursor.to_list(length=5)
    
    print(f"Retrieved {len(events)} events from vega_hackathon.vapi_events")
    for i, event in enumerate(events):
        print(f"--- Event {i+1} ---")
        print(json.dumps(event, indent=2, default=json_util.default))
    
    client.close()

if __name__ == "__main__":
    asyncio.run(inspect_events())
