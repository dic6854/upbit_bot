import pandas as pd
from datetime import datetime, time

# 파일 읽기
file_path = '코인_60분봉_org.xlsx'
df = pd.read_excel(file_path, sheet_name='비트코인')

# date 컬럼을 datetime으로 변환
df['date'] = pd.to_datetime(df['date'])

# 일자 컬럼 추가 (date.date())
df['day'] = df['date'].dt.date

# 월 컬럼 추가 (YYYY-MM)
df['month'] = df['date'].dt.to_period('M')

# 초기 자본금
capital = 1000000.0
fee_rate = 0.0005  # 0.05%

# 결과를 저장할 리스트
daily_results = []
profits_losses = {}  # dict: key=date_str, value={'profit': float, 'loss': float}

# 고유한 일자 목록 (정렬)
unique_days = sorted(df['day'].unique())

for day in unique_days:
    day_df = df[df['day'] == day]
    
    # 00:00 캔들 확인
    buy_mask = day_df['date'].dt.time == time(0, 0)
    if not buy_mask.any():
        continue  # 00:00 데이터 없으면 스킵
    
    # 11:00 캔들 확인
    sell_mask = day_df['date'].dt.time == time(11, 0)
    if not sell_mask.any():
        continue  # 11:00 데이터 없으면 스킵
    
    buy_price = day_df[buy_mask]['open'].values[0]
    sell_price = day_df[sell_mask]['close'].values[0]
    
    # 매수: BTC 수량 = capital * (1 - fee_rate) / buy_price
    btc_amount = capital * (1 - fee_rate) / buy_price
    
    # 매도: KRW = btc_amount * sell_price * (1 - fee_rate)
    new_capital = btc_amount * sell_price * (1 - fee_rate)
    
    # 손익 계산
    pl = new_capital - capital
    
    # 승패 기록
    win = 1 if pl > 0 else 0
    
    # dict 저장
    date_str = day.strftime('%Y-%m-%d')
    profit = pl if pl > 0 else 0.0
    loss = abs(pl) if pl < 0 else 0.0
    profits_losses[date_str] = {'profit': profit, 'loss': loss}
    
    # 결과 리스트에 추가
    daily_results.append({
        'date': date_str,
        'buy_price': buy_price,
        'sell_price': sell_price,
        'pl': pl,
        'win': win,
        'month': pd.Period(day, freq='M')
    })
    
    # 자본 업데이트
    capital = new_capital

# daily_results를 DataFrame으로 변환
results_df = pd.DataFrame(daily_results)

# 월별 통계
monthly_stats = []
for month in sorted(results_df['month'].unique()):
    month_df = results_df[results_df['month'] == month]
    
    total_pl = month_df['pl'].sum()
    total_profit = month_df[month_df['pl'] > 0]['pl'].sum()
    total_loss = month_df[month_df['pl'] < 0]['pl'].sum()  # 음수 값
    num_wins = month_df['win'].sum()
    num_losses = len(month_df) - num_wins
    total_trades = len(month_df)
    
    avg_profit = total_profit / num_wins if num_wins > 0 else 0
    avg_loss = total_loss / num_losses if num_losses > 0 else 0  # 음수
    
    # 손익비 = (평균 수익) / (평균 손실의 절대값)
    profit_factor = avg_profit / abs(avg_loss) if avg_loss != 0 else float('inf')
    
    # 승률
    win_rate = num_wins / total_trades if total_trades > 0 else 0
    
    monthly_stats.append({
        'month': str(month),
        'total_profit': total_profit,
        'total_loss': total_loss,
        'net_pl': total_pl,
        'profit_factor': profit_factor,
        'win_rate': win_rate
    })

# 월별 통계 출력
monthly_df = pd.DataFrame(monthly_stats)
print(monthly_df)

# profits_losses dict 출력 (예시로)
print(profits_losses)