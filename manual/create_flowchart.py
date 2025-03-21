import graphviz

# 플로우차트 생성
dot = graphviz.Digraph(comment='업비트 자동 거래 프로그램 플로우차트', format='png')
dot.attr(rankdir='TB', size='11,11', dpi='300')
dot.attr('node', shape='box', style='filled', fillcolor='lightblue', fontname='NanumGothic', fontsize='12')
dot.attr('edge', fontname='NanumGothic', fontsize='10')

# 메인 프로그램 시작
dot.node('start', '프로그램 시작', shape='oval', fillcolor='lightgreen')
dot.node('init', 'API 키 설정 및\n초기 자본금 설정')
dot.node('create_bot', 'UpbitTradingBot 객체 생성')
dot.node('run_bot', 'bot.run() 실행')

# 초기화 과정
dot.node('bot_init', 'UpbitTradingBot 초기화\n- API 연결 설정\n- 변수 초기화\n- 잔고 확인')

# 메인 루프
dot.node('main_loop', '메인 루프 시작', shape='oval')
dot.node('get_data', '5분봉 데이터 조회\n(get_ohlcv)')
dot.node('check_data', '데이터 충분?', shape='diamond')
dot.node('calc_sma', '20SMA 계산\n(calculate_sma)')
dot.node('print_status', '현재 상태 출력')
dot.node('check_holding', '코인 보유 중?', shape='diamond')

# 매수 신호 확인 및 실행
dot.node('check_buy', '매수 신호 확인\n(check_buy_signal)')
dot.node('buy_signal', '매수 신호 감지?', shape='diamond')
dot.node('execute_buy', '매수 실행\n(buy)')

# 매도 신호 확인 및 실행
dot.node('check_sell', '매도 신호 확인\n(check_sell_signal)')
dot.node('sell_signal', '매도 신호 감지?', shape='diamond')
dot.node('execute_sell', '매도 실행\n(sell)')

# 대기 및 반복
dot.node('wait', '5초 대기')
dot.node('loop_back', '루프 반복', shape='point')

# 예외 처리
dot.node('handle_error', '오류 처리', fillcolor='lightcoral')
dot.node('check_error_holding', '코인 보유 중?', shape='diamond', fillcolor='lightcoral')
dot.node('error_sell', '보유 코인 매도', fillcolor='lightcoral')
dot.node('end_error', '오류 종료', shape='oval', fillcolor='lightcoral')

# 정상 종료
dot.node('end', '프로그램 종료', shape='oval', fillcolor='lightgreen')

# 메인 프로그램 흐름
dot.edge('start', 'init')
dot.edge('init', 'create_bot')
dot.edge('create_bot', 'bot_init')
dot.edge('bot_init', 'run_bot')
dot.edge('run_bot', 'main_loop')

# 메인 루프 흐름
dot.edge('main_loop', 'get_data')
dot.edge('get_data', 'check_data')
dot.edge('check_data', 'calc_sma', label='Yes')
dot.edge('check_data', 'wait', label='No')
dot.edge('calc_sma', 'print_status')
dot.edge('print_status', 'check_holding')

# 코인 미보유 시 매수 로직
dot.edge('check_holding', 'check_buy', label='No')
dot.edge('check_buy', 'buy_signal')
dot.edge('buy_signal', 'execute_buy', label='Yes')
dot.edge('buy_signal', 'wait', label='No')
dot.edge('execute_buy', 'wait')

# 코인 보유 시 매도 로직
dot.edge('check_holding', 'check_sell', label='Yes')
dot.edge('check_sell', 'sell_signal')
dot.edge('sell_signal', 'execute_sell', label='Yes')
dot.edge('sell_signal', 'wait', label='No')
dot.edge('execute_sell', 'wait')

# 루프 반복
dot.edge('wait', 'loop_back')
dot.edge('loop_back', 'get_data')

# 예외 처리 흐름
dot.edge('main_loop', 'handle_error', label='Exception', style='dashed')
dot.edge('handle_error', 'check_error_holding')
dot.edge('check_error_holding', 'error_sell', label='Yes')
dot.edge('check_error_holding', 'end_error', label='No')
dot.edge('error_sell', 'end_error')

# 정상 종료 (KeyboardInterrupt)
dot.edge('main_loop', 'end', label='KeyboardInterrupt', style='dashed')

# 서브 플로우차트: 매수 함수
buy_dot = graphviz.Digraph(name='cluster_buy')
buy_dot.attr(label='매수 함수 (buy)', style='filled', color='lightgrey')
buy_dot.node('buy_start', '매수 시작', shape='oval')
buy_dot.node('check_already_holding', '이미 보유 중?', shape='diamond')
buy_dot.node('get_price', '현재 가격 조회')
buy_dot.node('calc_amount', '최대 매수 수량 계산\n(수수료 고려)')
buy_dot.node('place_buy_order', '매수 주문 실행')
buy_dot.node('check_order_success', '주문 성공?', shape='diamond')
buy_dot.node('update_balance', '잔고 업데이트\nis_holding = True')
buy_dot.node('buy_return_true', 'True 반환', shape='oval')
buy_dot.node('buy_return_false', 'False 반환', shape='oval')

buy_dot.edge('buy_start', 'check_already_holding')
buy_dot.edge('check_already_holding', 'buy_return_false', label='Yes')
buy_dot.edge('check_already_holding', 'get_price', label='No')
buy_dot.edge('get_price', 'calc_amount')
buy_dot.edge('calc_amount', 'place_buy_order')
buy_dot.edge('place_buy_order', 'check_order_success')
buy_dot.edge('check_order_success', 'update_balance', label='Yes')
buy_dot.edge('check_order_success', 'buy_return_false', label='No')
buy_dot.edge('update_balance', 'buy_return_true')

dot.subgraph(buy_dot)

# 서브 플로우차트: 매도 함수
sell_dot = graphviz.Digraph(name='cluster_sell')
sell_dot.attr(label='매도 함수 (sell)', style='filled', color='lightgrey')
sell_dot.node('sell_start', '매도 시작', shape='oval')
sell_dot.node('check_not_holding', '보유 중이 아님?', shape='diamond')
sell_dot.node('get_coin_balance', '보유 코인 수량 확인')
sell_dot.node('check_has_balance', '보유 수량 > 0?', shape='diamond')
sell_dot.node('place_sell_order', '매도 주문 실행')
sell_dot.node('check_sell_success', '주문 성공?', shape='diamond')
sell_dot.node('get_krw_balance', 'KRW 잔고 확인')
sell_dot.node('check_profit', '수익 발생?', shape='diamond')
sell_dot.node('update_profit', '수익금 업데이트\n자본금 = 초기 자본금')
sell_dot.node('update_capital', '자본금 = 현재 잔고')
sell_dot.node('reset_holding', 'is_holding = False\ncoin_balance = 0')
sell_dot.node('sell_return_true', 'True 반환', shape='oval')
sell_dot.node('sell_return_false', 'False 반환', shape='oval')

sell_dot.edge('sell_start', 'check_not_holding')
sell_dot.edge('check_not_holding', 'sell_return_false', label='Yes')
sell_dot.edge('check_not_holding', 'get_coin_balance', label='No')
sell_dot.edge('get_coin_balance', 'check_has_balance')
sell_dot.edge('check_has_balance', 'place_sell_order', label='Yes')
sell_dot.edge('check_has_balance', 'reset_holding', label='No')
sell_dot.edge('reset_holding', 'sell_return_false')
sell_dot.edge('place_sell_order', 'check_sell_success')
sell_dot.edge('check_sell_success', 'get_krw_balance', label='Yes')
sell_dot.edge('check_sell_success', 'sell_return_false', label='No')
sell_dot.edge('get_krw_balance', 'check_profit')
sell_dot.edge('check_profit', 'update_profit', label='Yes')
sell_dot.edge('check_profit', 'update_capital', label='No')
sell_dot.edge('update_profit', 'reset_holding')
sell_dot.edge('update_capital', 'reset_holding')
sell_dot.edge('reset_holding', 'sell_return_true')

dot.subgraph(sell_dot)

# 플로우차트 저장
dot.render('/home/ubuntu/upbit_trading_bot_flowchart', cleanup=True)
print("플로우차트가 생성되었습니다: /home/ubuntu/upbit_trading_bot_flowchart.png")
