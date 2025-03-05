from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

# kst = "2025-02-28 23:58:00"

# kst = datetime.strptime(kst, "%Y-%m-%d %H:%M:%S")
# kst1 = kst - timedelta(minutes=525600)

# print(kst1)

# date1 = datetime(2024, 2, 1, 9, 30, 0)
# date2 = datetime(2025, 3, 3, 15, 45, 30)

# time_difference = relativedelta(date2, date1)

# print("chd:", time_difference)
# print("년:", time_difference.years)
# print("월:", time_difference.months)
# print("일:", time_difference.days)
# print("시간:", time_difference.hours)
# print("분:", time_difference.minutes)
# print("초:", time_difference.seconds)

date_format = "%Y-%m-%d %H:%M:%S"  # 날짜 형식 정의

date1_str = "2023-03-02 00:00:00"
date2_str = "2024-03-02 00:00:00"

date1 = datetime.strptime(date1_str, date_format)
date2 = datetime.strptime(date2_str, date_format)

# print(f"Type of date1 : {type(date1)}")

# if type(date1) == datetime:
#     print("This is Datetime")

time_difference = date2 - date1

minutes_difference = time_difference.total_seconds() / 60
print(f"분 차이: {minutes_difference:,.0f}분")
hours_difference = time_difference.total_seconds() / (60*60)
print(f"시 차이: {hours_difference:,.0f}시")
days_difference = time_difference.total_seconds() / (60*60*24)
print(f"일 차이: {days_difference:,.0f}일")

date3 = date2 - timedelta(days=365)
print(f"\ndate3 : {date3}")

# df = pyupbit.get_ohlcv_from(ticker="KRW-BTC", interval="minute5", fromDatetime=date1, to=date2)
# print(df)