import pyupbit
import pandas as pd
from datetime import datetime
import os


def get_keys():
    access_key = os.environ['UPBIT_ACCESS_KEY']
    secret_key = os.environ['UPBIT_SECRET_KEY']

    return access_key, secret_key

def get_trade_datetime(uuid):
    order = upbit.get_individual_order(uuid)
    created_at = order['trades'][0]['created_at']
    ldatetime = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S%z")
    tmp_str_datetime = ldatetime.strftime("%Y-%m-%d %H:%M:%S")
    trade_datetime = datetime.strptime(tmp_str_datetime, "%Y-%m-%d %H:%M:%S")
    return trade_datetime


if __name__ == "__main__":
    ACCESS_KEY, SECRET_KEY = get_keys()
    upbit = pyupbit.Upbit(ACCESS_KEY, SECRET_KEY)

    # 주문 내역 조회
    market = "KRW-BTC"  # 조회할 마켓 (선택 사항)
    state = "done"      # 상태 필터링: "done" (체결 완료), "wait" (대기 중), "cancel" (취소)
    orders = upbit.get_order(ticker_or_uuid=market, state=state)
    created_at = orders[0]['created_at']
    ldatetime = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S%z")
    tmp_str_datetime = ldatetime.strftime("%Y-%m-%d %H:%M:%S")
    trade_datetime = datetime.strptime(tmp_str_datetime, "%Y-%m-%d %H:%M:%S")
    # uuid = orders[0]['uuid']
    # order = upbit.get_individual_order(uuid)
    # created_at = order['trades'][0]['created_at']
    # ldatetime = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S%z")
    # tmp_str_datetime = ldatetime.strftime("%Y-%m-%d %H:%M:%S")
    # trade_datetime = datetime.strptime(tmp_str_datetime, "%Y-%m-%d %H:%M:%S")
    print(created_at)