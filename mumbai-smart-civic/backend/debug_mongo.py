import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def debug_mongo():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    dbs = await client.list_database_names()
    print(f"Databases: {dbs}")
    
    for db_name in ["mumbai_smart_civic", "vega_hackathon"]:
        if db_name in dbs:
            db = client[db_name]
            cols = await db.list_collection_names()
            print(f"Collections in {db_name}: {cols}")
            if "vapi_events" in cols:
                count = await db["vapi_events"].count_documents({})
                print(f"  vapi_events count: {count}")
                latest = await db["vapi_events"].find_one(sort=[("_id", -1)])
                if latest:
                    print(f"  Latest event callId: {latest.get('callId')}")

    client.close()

if __name__ == "__main__":
    asyncio.run(debug_mongo())
