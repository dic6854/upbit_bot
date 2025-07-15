import pyupbit
import pandas as pd
import os
import time

def process_csv(in_file_name, out_file_name):
    df = pd.read_csv(in_file_name, header=None, index_col=0)
    df.columns = ['open', 'high', 'low', 'close', 'volume', 'value']
    df.index.name = ''

    df['volume'] = df['volume'].astype(float).round(8)
    df['value'] = df['value'].astype(float).round(6)

    df.to_excel(out_file_name, index=True)

if __name__ == "__main__":
    krw_tickers = pyupbit.get_tickers(fiat="KRW")

    ct = 26
    tc = len(krw_tickers)
    for i in range(25, tc):
        ticker = krw_tickers[i]
        input_file_name = f"data/{ticker}.xlsx"
        output_file_name1 = f"cdata/{ticker}_m1.csv"
        output_file_name5 = f"cdata/{ticker}_m5.csv"

        if os.path.exists(input_file_name):
            old_df = pd.read_excel(io=input_file_name, sheet_name=None, engine='openpyxl', index_col=0, parse_dates=True)

            df_m5 = old_df['minute5']
            df_m1 = old_df['minute1']

            df_m5.to_csv(output_file_name5)
            df_m1.to_csv(output_file_name1)
            print(f"[{ct} / {tc}] - [{output_file_name1}] 쓰기 종료")
            ct += 1
