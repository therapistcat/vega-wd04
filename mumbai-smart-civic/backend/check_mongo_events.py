import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def check_mongo():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["vega_hackathon"]
    event = await db["vapi_events"].find_one({"callId": "verify_test_call_999"})
    if event:
        print(f"Match Found!")
        print(f"Call ID: {event.get('callId')}")
        print(f"Type: {event.get('type')}")
        print(f"Received At: {event.get('receivedAt')}")
    else:
        print("No event found with callId: verify_test_call_999")
    client.close()

if __name__ == "__main__":
    asyncio.run(check_mongo())
