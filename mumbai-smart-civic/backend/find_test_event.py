import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def find_anywhere():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    dbs = await client.list_database_names()
    print(f"Searching for 'verify_test_call_999' across {len(dbs)} databases...")
    
    found = False
    for db_name in dbs:
        db = client[db_name]
        try:
            cols = await db.list_collection_names()
            for col_name in cols:
                # Search for doc with callId or call_id matching our test
                doc = await db[col_name].find_one({
                    "$or": [
                        {"callId": "verify_test_call_999"},
                        {"call_id": "verify_test_call_999"},
                        {"payload.call.id": "verify_test_call_999"},
                        {"payload.message.call.id": "verify_test_call_999"}
                    ]
                })
                if doc:
                    print(f"MATCH FOUND in DB: {db_name} | Collection: {col_name}")
                    print(f"Document keys: {list(doc.keys())}")
                    found = True
        except Exception as e:
            pass
            
    if not found:
        print("Not found anywhere in MongoDB.")
    client.close()

if __name__ == "__main__":
    asyncio.run(find_anywhere())
