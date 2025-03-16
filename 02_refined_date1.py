import pandas as pd
from datetime import datetime, timedelta

# ticker = krw_tickers[i]
ticker = "KRW-BTC"

for i in range(1, 6, 4):

    file_name = f"test/{ticker}_m{i}.csv"

    df = pd.read_csv(file_name, index_col=0)
    df.index = pd.to_datetime(df.index, format="%Y-%m-%d %H:%M:%S")
    lenth_of_df = len(df)
    print(f"Lenth of df : {lenth_of_df}")

    df_refined = pd.DataFrame()
    while True:
        cut_start = df.index[0]
        cut_end = cut_start + pd.Timedelta(days=1)

        time_difference = cut_end - cut_start
        total_count = int((time_difference.total_seconds() / 60) / i) + 1
        print(f"total_count = {total_count}")

        df_t = df[(df.index >= cut_start) & (df.index <= cut_end)]
        lenth_of_df_t = len(df_t)
        print(f"Lenth of df_t : {lenth_of_df_t}")
        print(df_t)

        if total_count == lenth_of_df_t:
            print("Skeep processing")
            break
        else:
            if total_count < lenth_of_df_t:
                print("Over the Data Processing")

        if total_count > lenth_of_df_t:
            print("Missing Data Processing")

            interval = timedelta(minutes=i)
            new_index = pd.date_range(df_t.index.min(), df_t.index.max(), freq=interval)
            print(f"interval={interval}, lenth of new_index = {len(new_index)}")
            print(f"new_index={new_index}")
            df_t = df_t.reindex(new_index)
            df_t = df_t.ffill()

            lenth_of_df_t = len(df_t)
            print(f"Refined Lenth of df_t : {lenth_of_df_t}")
        '''
        el
            
            break
        else:
        ''' 
 



    break
    # first_dt = df.index[0]
    # print(f"First Datetime : {first_dt}")

    # for j in range(lenth_of_df):

