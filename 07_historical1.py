import pandas as pd
df = pd.DataFrame()
df1 = pd.read_excel('코인_5분봉_2026년.xlsx')
df2 = pd.read_excel('코인_5분봉_2025년.xlsx')
df3 = pd.read_excel('코인_5분봉_2024년.xlsx')

df = pd.concat([df1, df2, df3], ignore_index=True)
df.sort_index(ascending=False, inplace=True)

df.to_excel("코인_5분봉.xlsx", index=False, sheet_name="비트코인")
print("저장완료!")
