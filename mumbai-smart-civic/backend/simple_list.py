import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def simple_list():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    dbs = await client.list_database_names()
    for db_name in dbs:
        db = client[db_name]
        try:
            cols = await db.list_collection_names()
            if "vapi_events" in cols:
                count = await db["vapi_events"].count_documents({})
                latest = await db["vapi_events"].find_one(sort=[("_id", -1)])
                # Check for new callId (verify_test_call_999) or old call_id
                cid = latest.get("callId") or latest.get("call_id")
                print(f"DB: {db_name} | Collection: vapi_events | Count: {count} | Latest CID: {cid}")
            else:
                print(f"DB: {db_name} | Collections: {cols}")
        except:
            print(f"DB: {db_name} | ACCESS ERROR")
    client.close()

if __name__ == "__main__":
    asyncio.run(simple_list())
