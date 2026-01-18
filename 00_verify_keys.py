# 업비트에 등록된 키 (환경변수로 등록하기 전) 확인 및 잔고 조회

import pyupbit
from get_keys import get_keys

myAccess_key, mySecret_key = get_keys()

print(f"myAccess_key = {myAccess_key}")
print(f"mySecret_key = {mySecret_key}")

upbit = pyupbit.Upbit(access=myAccess_key, secret=mySecret_key)

balances = upbit.get_balances()

for balance in balances:
    print(balance)
