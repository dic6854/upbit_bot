import pymongo
from datetime import datetime

ID = 'jns01'
PW = 'jns01'
conn = pymongo.MongoClient(f'mongodb://{ID}:{PW}@192.168.5.192:27017/upbitdb')
db = conn.upbitdb
myCollection = db.mycoin

candle = {
    "time": datetime(2025, 3, 17, 12, 0, 0),
    "open": 57040000,
    "high": 57140000,
    "low": 57000000,
    "close": 57137000,
    "volume": 7.42317328,
    "value": 423903854.91162
}

myCollection.insert_one(candle)
# print(myCollection)
