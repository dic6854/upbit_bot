import pyupbit
import pandas as pd
from datetime import datetime, timedelta

def refining_data(df, start_datetime, end_datetime, unit_m):
    df_t = df[(df.index >= start_datetime) & (df.index <= end_datetime)].copy()

    actual_count = len(df_t)
    delta = end_datetime - start_datetime
    expected_count = int((delta.total_seconds() / 60) / unit_m) + 1

    # print(f"actual_count={actual_count}, expected_count={expected_count}")

    s_unit_m = f"{unit_m}min"
    if actual_count == expected_count:
        # print(f"[{start_datetime}] ~ [{end_datetime}]: 정상적인 데이터 개수.")
        df_t = df_t
    elif actual_count < expected_count:
        # print(f"[{start_datetime}] ~ [{end_datetime}]: 데이터가 {expected_count}개 미만. 보정 시작.")
        expected_index = pd.date_range(start=start_datetime, end=end_datetime, freq=s_unit_m)
        df_t = df_t.reindex(expected_index, method='ffill')
        # print(f"보정 후 행 수: {len(df_t)}")
    elif actual_count > expected_count:
        print(f"[{start_datetime}] ~ [{end_datetime}]: 데이터가 {expected_count}개 초과. 보정 시작.")
        df_t = df_t[~df_t.index.duplicated(keep='last')]
        # print(f"중복 제거 후 행 수: {len(df_t)}")
        
        if len(df_t) > expected_count:
            expected_index = pd.date_range(start=start_datetime, end=end_datetime, freq=s_unit_m)
            df_t = df_t.reindex(expected_index).dropna()
            # print(f"기대 인덱스에 맞춘 후 Row(행) 수: {len(df_t)}")

    return df_t


def refining_coin(ticker):
    for i in range(1, 6, 4):
        file_name = f"cdata/{ticker}_m{i}.csv"

        df = pd.read_csv(file_name, index_col=0)
        try:
            df.index = pd.to_datetime(df.index, format="%Y-%m-%d %H:%M:%S")
        except:
            df.index = pd.to_datetime(df.index, format="%Y-%m-%d %H:%M")

        df = df[~df.index.duplicated(keep='last')]

        result_df = pd.DataFrame()

        start_datetime = df.index[0]
        end_datetime = df.index[-1]

        sdate = start_datetime
        edate = start_datetime.replace(hour=8, minute=55, second=0)

        if start_datetime < edate:
            df_t = refining_data(df, sdate, edate, i)
            result_df = pd.concat([result_df, df_t])
            # print(f"N_df_t : {len(df_t)}, N_result_df : {len(result_df)}")
            start_datetime = result_df.index[-1]
        
        current_datetime = start_datetime

        while current_datetime <= end_datetime:
            sdate = current_datetime.replace(hour=8, minute=55, second=0)
            edate = sdate + pd.Timedelta(days=1)
            if end_datetime <= edate:
                edate = end_datetime

            # print(f"sdate={sdate}, edate={edate}")

            df_t = refining_data(df, sdate, edate, i)
            result_df = pd.concat([result_df, df_t])
            current_datetime += timedelta(days=1)

        result_df = result_df[~result_df.index.duplicated(keep='last')]
        result_df = result_df.dropna(how='all')

        file_name = f"hdata/{ticker}_m{i}.csv"
        result_df.to_csv(file_name)

        print(f"[ {ct} / {tt} ] - {file_name} 파일 저장 완료")


if __name__ == "__main__":
    krw_tickers = pyupbit.get_tickers(fiat="KRW")

    tt = len(krw_tickers)
    ct = 1
    for i in range(tt):
        ticker = krw_tickers[i]
        refining_coin(ticker)

        ct += 1