import os
import json
import time
from execution.weex_adapter import WeexExecutionAdapter

def apply_rescue():
    adapter = WeexExecutionAdapter(
        api_key=os.getenv("WEEX_API_KEY"),
        secret_key=os.getenv("WEEX_SECRET_KEY"),
        passphrase=os.getenv("WEEX_PASSPHRASE"),
        default_symbol="cmt_btcusdt"
    )
    
    targets = {
        "cmt_bnbusdt": "short",
        "cmt_ltcusdt": "long",
        "cmt_solusdt": "long"
    }
    
    print("\n--- FETCHING POSITIONS ---")
    pos_res = adapter.get_positions()
    positions = pos_res if isinstance(pos_res, list) else pos_res.get('data', [])
    
    active_map = {p['symbol']: p for p in positions}
    
    for symbol, expected_side in targets.items():
        if symbol not in active_map:
            print(f"⚠️ {symbol} position not found in API.")
            continue
            
        pos = active_map[symbol]
        size = abs(float(pos.get('holdAmount', pos.get('size', 0))))
        side = pos.get('side', '').lower()
        if side == '2' or side == 'short': side = 'short'
        else: side = 'long'
        
        # Get Current Price for SL calculation
        ticker = adapter.get_ticker(symbol)
        curr_price = float(ticker['last'])
        
        # Safety Stop (1.5% distance)
        if side == 'short':
            sl_price = curr_price * 1.015
        else:
            sl_price = curr_price * 0.985
            
        # Get Price Step for rounding
        rules = adapter.get_symbol_rules(symbol)
        p_step = rules.get('price_step', 0.1)
        # Round to step
        sl_price = round(round(sl_price / p_step) * p_step, 4)
        if p_step >= 1: sl_price = int(sl_price)
        
        print(f"Applying SL for {symbol} ({side.upper()}): Size={size}, Price={sl_price} (1.5% from {curr_price})")
        
        adapter.symbol = symbol
        res = adapter.place_tp_sl_order(
            plan_type='loss_plan',
            trigger_price=sl_price,
            size=size,
            position_side=side
        )
        print(f"Result: {json.dumps(res)}")

if __name__ == "__main__":
    apply_rescue()
