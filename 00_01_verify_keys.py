# 업비트에 등록된 키 (환경변수로 등록된 후) 확인 및 잔고 조회

import pyupbit
import os

def get_keys():
    access_key = os.environ['UPBIT_ACCESS_KEY']
    secret_key = os.environ['UPBIT_SECRET_KEY']

    return access_key, secret_key

if __name__ == "__main__":
    # 로그인
    myAccess_key, mySecret_key = get_keys()

    print(f"My Access Kery : {myAccess_key}")
    print(f"My Secret Kery : {mySecret_key}")

    # 내 잔고 조회
    upbit = pyupbit.Upbit(access=myAccess_key, secret=mySecret_key)
    balances = upbit.get_balances()

    for balance in balances:
        print(balance)
