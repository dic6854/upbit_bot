import pyupbit
from datetime import datetime, timedelta
import pandas as pd

date1_str = "2024-03-02 00:00:00"
date2_str = "2025-03-02 00:00:00"

def set_datetime(date: str | pd.Timestamp | datetime | None) -> datetime:
    if date is None:
        date = datetime.now()
        date_format = "%Y-%m-%d %H:%M:%S"
        date = datetime.strftime(date, date_format)
        date = datetime.strptime(date, date_format)
        return date
    elif isinstance(date, str):
        try:
            return pd.to_datetime(date).to_pydatetime()
        except ValueError:
            print(f"Invalid date string: {date}")
            return -1
    elif isinstance(date, pd.Timestamp):
        return date.to_pydatetime()
    elif isinstance(date, datetime):
        return date
    else:
      print(f"Unsupported date type: {type(date)}")
      return -2

if __name__ == "__main__":
    # date = set_datetime(None)
    # print(date)

    date1_str = "2025-02-02 09:00:20"
    date2_str = "2024-02-02 07:25:15"

    date_format = "%Y-%m-%d %H:%M:%S"

    date1 = datetime.strptime(date1_str, date_format)
    date2 = datetime.strptime(date2_str, date_format)

    time_difference = date1 - date2
    total_minute1, total_second = divmod(time_difference.total_seconds(), 60)
    total_hour1, total_minute = divmod(total_minute1, 60)
    total_day, total_hour = divmod(total_hour1, 24)

    print(f"total_day : {total_day:,.0f}")
    print(f"total_hour : {total_hour:,.0f}")
    print(f"total_minute : {total_minute:,.0f}")
    print(f"total_second : {total_second:,.0f}")

    date3 = date1 - timedelta(days=total_day, hours=total_hour, minutes=total_minute, seconds=total_second)
    print(f"date3 : {date3}")
    date4 = date1 - timedelta(seconds=time_difference.total_seconds())
    print(f"date4 : {date4}")

    tm = total_day * 24 * 60 + total_hour * 60 + total_minute
    if total_second > 0:
        tm += 1
    date5 = date1 - timedelta(seconds=time_difference.total_seconds())
    print(f"\ndate5 : {date5}")

    date5_1 = date5.replace(second=0)
    print(f"date5_1 : {date5_1}")

    date5_str = datetime.strftime(date5, "%Y-%m-%d %H:%M:00")
    date6 = datetime.strptime(date5_str, date_format)
    print(f"date5_str : {date5_str}")
    print(f"date6 : {date6}")