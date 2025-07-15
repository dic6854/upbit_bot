# 업비트에 등록된 키 (환경변수로 등록하기 전) 확인 및 잔고 조회

import pyupbit

access_key = "tYrgW4vSBodQjNT31RWdzeVkR1o9MEpqqMwksowp"
secret_key = "ySwagxxcQEojjExUMpuuo8SyWDEiRs522z0hDx7H"

upbit = pyupbit.Upbit(access=access_key, secret=secret_key)

balances = upbit.get_balances()

for balance in balances:
    print(balance)
