import pyupbit
from get_keys import get_keys

access_key, secret_key = get_keys()

# 로그인
upbit = pyupbit.Upbit(access_key, secret_key)

# 내 잔고 조회
balances = upbit.get_balances()

for balance in balances:
    print(balance)