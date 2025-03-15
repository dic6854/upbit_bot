from datetime import datetime
import pandas as pd

mydatetime = []
mydatetime = ["2025-03-12 08:55:00", "2025-03-12 09:00:00", "2025-03-12 09:05:00", "2025-03-13 08:45:00", "2025-03-13 08:55:00", "2025-03-13 09:00:00", "2025-03-13 09:05:00"]

for i in range(len(mydatetime)):
    curr_datetime = mydatetime[i]
    curr_datetime = datetime.strptime(curr_datetime, "%Y-%m-%d %H:%M:%S")
    curr_time = curr_datetime.time()

    if curr_time == pd.Timestamp("08:50:00").time():
        print("수익 계산 마감")
    elif curr_time == pd.Timestamp("09:00:00").time():
        print("수익 계산 시작")
    elif (curr_time > pd.Timestamp("08:50:00").time()) and (curr_time < pd.Timestamp("09:00:00").time()):
        print("정산 계산 중")
    else:
        print("수익 계산 중중")
