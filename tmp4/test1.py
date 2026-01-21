import logging

# 로깅 설정
logging.basicConfig(
    filename="sma_breakout_log.txt",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

logging.info(f"총 181개 코인 조회 시작")