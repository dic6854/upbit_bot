import pyupbit
import os


def get_keys():
    access_key = os.environ['UPBIT_ACCESS_KEY']
    secret_key = os.environ['UPBIT_SECRET_KEY']

    return access_key, secret_key

def get_average_sell_price(order_uuid):
    order_info = upbit.get_order(order_uuid)
    if order_info and order_info.get('state') == 'done':
        trades = order_info.get('trades')
        if trades:
            total_sell_price = 0
            total_sell_volume = 0

            for trade in trades:
                price = float(trade['price'])
                volume = float(trade['volume'])
                total_sell_price += price * volume
                total_sell_volume += volume
            if total_sell_volume > 0:
                average_sell_price = total_sell_price / total_sell_volume
                return average_sell_price
            else:
                return False
        else:
            return False
    else:
        return False


ACCESS_KEY, SECRET_KEY = get_keys()

upbit = pyupbit.Upbit(ACCESS_KEY, SECRET_KEY)

krw_balance = upbit.get_balance("KRW")
print(f"krw_balance = {krw_balance:,.0f}")

coin_balance = upbit.get_balance("BTC")
print(f"coin_balance = {coin_balance:,.8f}")

trades = upbit.get_order(ticker_or_uuid="KRW-BTC", state='done')
trade = trades[0]
order_uuid = trade['uuid']
# order_info = upbit.get_order(uuid)
# print(order_info)
# trades = order_info['trades']
# print(trades)
sell_avrg_price = float(get_average_sell_price(order_uuid))
print(f"sell_avrg_price = {sell_avrg_price:,.0f}")
sell_volume = float(trade['volume'])
print(f"sell_volume = {sell_volume:,.8f}")
total_sell_price = sell_avrg_price * sell_volume
print(f"total_sell_price = {total_sell_price:,.0f}")

