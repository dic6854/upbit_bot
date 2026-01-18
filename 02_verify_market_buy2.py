# 시장가 매수 확인

import pyupbit
import os
import time
from datetime import datetime, timedelta

def get_keys():
    access_key = os.environ['UPBIT_ACCESS_KEY']
    secret_key = os.environ['UPBIT_SECRET_KEY']

    return access_key, secret_key

if __name__ == "__main__":
    # 로그인
    myAccess_key, mySecret_key = get_keys()
    upbit = pyupbit.Upbit(access=myAccess_key, secret=mySecret_key)

    uuid = 'cbfb900e-853b-45f2-9c64-e27a68d6c774'

    order_info = upbit.get_order(uuid)

    print(order_info)




