    def consolidate_hedged_positions(self):
        """
        Detect and consolidate hedged positions (LONG + SHORT on same symbol).
        Automatically closes both sides when net exposure is below 5%.
        """
        # Group positions by symbol
        symbol_positions = {}
        for symbol, size in self.positions.items():
            base_symbol = symbol  # Already using full symbol names
            if base_symbol not in symbol_positions:
                symbol_positions[base_symbol] = []
            symbol_positions[base_symbol].append(size)
        
        # Detect hedges
        for symbol, sizes in symbol_positions.items():
            if len(sizes) < 2:
                continue  # No hedge possible with single position
            
            # Calculate net position
            net_size = sum(sizes)
            total_abs = sum(abs(s) for s in sizes)
            
            # Check if hedged (opposing positions exist)
            has_long = any(s > 0 for s in sizes)
            has_short = any(s < 0 for s in sizes)
            
            if has_long and has_short and total_abs > 0:
                # Calculate net exposure as % of total
                net_exposure_pct = abs(net_size) / total_abs * 100 if total_abs > 0 else 0
                
                # Consolidate if net exposure < 5%
                if net_exposure_pct < 5.0:
                    logger.warning(f"🔄 [{symbol}] HEDGE DETECTED: Net {net_size:.4f}, Total {total_abs:.4f} ({net_exposure_pct:.1f}% net)")
                    logger.info(f"   Consolidating to eliminate funding waste...")
                    
                    try:
                        self.adapter.symbol = symbol
                        result = self.adapter.close_all_positions(symbol)
                        
                        if result and isinstance(result, list):
                            success_count = sum(1 for r in result if r.get('success'))
                            logger.info(f"   ✓ Closed {success_count} hedged positions on {symbol}")
                            
                            # Update local state
                            self.positions[symbol] = 0.0
                            self.active_trades[symbol] = []
                        else:
                            logger.warning(f"   ⚠️  Hedge consolidation failed for {symbol}: {result}")
                    
                    except Exception as e:
                        logger.error(f"   Error consolidating hedge on {symbol}: {e}")
