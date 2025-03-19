from datetime import datetime, timedelta

# 시작 날짜와 종료 날짜 설정
start_date = datetime(2024, 4, 11)
end_date = datetime(2025, 3, 19)

# 년 단위 루프
current_year = start_date.year
while current_year <= end_date.year:
    print(f"Year: {current_year}")

    # 월 단위 루프
    current_month = start_date.month if current_year == start_date.year else 1
    while current_month <= 12:
        print(f"  Month: {current_month}")

        # 일 단위 루프
        # 현재 월의 첫 날과 마지막 날 계산
        if current_month == 12:
            next_month = 1
            next_year = current_year + 1
        else:
            next_month = current_month + 1
            next_year = current_year

        first_day_of_month = datetime(current_year, current_month, 1)
        last_day_of_month = datetime(next_year, next_month, 1) - timedelta(days=1)

        # 시작 날짜와 종료 날짜를 고려하여 일 단위 루프 범위 설정
        loop_start_date = max(start_date, first_day_of_month)
        loop_end_date = min(end_date, last_day_of_month)

        current_day = loop_start_date.day
        while current_day <= loop_end_date.day:
            current_date = datetime(current_year, current_month, current_day)
            print(f"    Day: {current_date.strftime('%Y-%m-%d')}")
            current_day += 1

        # 월 단위 루프 종료 조건
        if current_year == end_date.year and current_month == end_date.month:
            break
        current_month += 1

    # 년 단위 �프 종료 조건

    if current_year == end_date.year:
        break
    current_year += 1