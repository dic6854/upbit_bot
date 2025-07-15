import pyupbit
import os

def get_keys():
    access_key = os.environ['UPBIT_ACCESS_KEY']
    secret_key = os.environ['UPBIT_SECRET_KEY']

    return access_key, secret_key


if __name__ == "__main__":
    access_key, secret_key = get_keys()

    # 로그인
    upbit = pyupbit.Upbit(access_key, secret_key)

    # 내 잔고 조회
    balances = upbit.get_balances()

    for balance in balances:
        print(balance)