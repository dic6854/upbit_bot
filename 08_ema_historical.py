import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 1-1. 엑셀파일 읽어들임
file_name = "코인_5분봉_org.xlsx"
df = pd.read_excel(file_name)
df = df.sort_values(by='date', ascending=True).reset_index(drop=True)
print("읽어들임 완료!!")

# 1-2. EMA200, EMA9, EMA21 지표 계산
df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()

# 1-3. RSI 지표 계산 (Stochastic RSI를 위해)
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

df['RSI'] = calculate_rsi(df['close'], 14)

# 1-4. Stochastic RSI 계산 (14, 14, 3, 3)
# 1-4-1. Stochastic RSI = (RSI - Lowest RSI) / (Highest RSI - Lowest RSI) over 14 periods   
df['StochRSI'] = (df['RSI'] - df['RSI'].rolling(14).min()) / (df['RSI'].rolling(14).max() - df['RSI'].rolling(14).min())

# 1-4-2. %K: 3-period SMA of StochRSI
df['StochRSI_K'] = df['StochRSI'].rolling(3).mean() * 100  # 0-100 스케일

# 1-4-3. %D: 3-period SMA of %K
df['StochRSI_D'] = df['StochRSI_K'].rolling(3).mean()

# 1-5. NaN 제거 (지표 계산으로 인한)
df.dropna(inplace=True)

df.to_excel("코인_5분봉_ema_rsi_stochrsi.xlsx", index=False, sheet_name="비트코인")
print("저장완료!")