import pyupbit
import pandas as pd
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

    ct = 1
    tc = len(krw_tickers)
    for i in range(tc):
        coin = krw_tickers[i].split("-")[1]
        input_file_name = f"hdata/{coin}_m5.csv"
        output_file_name = f"data/{coin}_m5.xlsx"

        process_csv(input_file_name, output_file_name)
        print(f"[{ct} / {tc}] - {output_file_name} file is saved.")
        ct = ct + 1
        time.sleep(1)