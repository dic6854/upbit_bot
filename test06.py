import pyupbit
import pandas as pd

krw_tickers = pyupbit.get_tickers(fiat="KRW")

print(f"type of krw_tickers : {type(krw_tickers)}")
coin = krw_tickers[0].split("-")[1]
print(f"coin : {coin}")

df = pd.DataFrame(krw_tickers, columns=['ticker'])
df.index = range(len(df))

print(df)

fn = "hdata/00_tickers.csv"
df.to_csv(path_or_buf=fn, mode='a', header=True)
print(f"{fn} 파일 저장 완료!")