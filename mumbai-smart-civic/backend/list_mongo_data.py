import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def list_all_data():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    dbs = await client.list_database_names()
    print("ALL DATABASES:")
    for db_name in dbs:
        print(f"  - {db_name}")
        db = client[db_name]
        try:
            cols = await db.list_collection_names()
            for col in cols:
                count = await db[col].count_documents({})
                print(f"    * {col} ({count} docs)")
                if col == "vapi_events":
                    latest = await db[col].find_one(sort=[("_id", -1)])
                    if latest:
                        # Print something unique to identify which logic stored it
                        keys = list(latest.keys())
                        print(f"      Keys: {keys}")
                        if "callId" in latest:
                            print(f"      Latest callId: {latest.get('callId')}")
                        elif "call_id" in latest:
                            print(f"      Latest call_id: {latest.get('call_id')}")
        except Exception as e:
            print(f"    Error listing collections in {db_name}: {e}")
    client.close()

if __name__ == "__main__":
    asyncio.run(list_all_data())
