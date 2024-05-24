import pandas as pd
import numpy as np
import pandas_ta as ta
import talib
from signals import Signal
from ib_insync import *

from config import StrategyConfig
from signals import Signal


class Strategy(object):
    def __init__(self, ib: IB, config: StrategyConfig):
        self.ib = ib
        self.config = config

    def run(self):
        # while receiving real time data, call on_data method
        with self.ib.reqTickByTickData(self.main_instrument, 'Last', 0) as main_data:
            additional_data = dict()
            for additional_instrument in self.additional_data_sources:
                additional_data[additional_instrument.symbol] = (
                    self.ib.reqTickByTickData(additional_instrument, 'Last', 0)
                )
            while True:
                try:
                    self.on_data(main_data) # additional_data
                except ConnectionError:
                    print("Connection error. Reconnecting...")
                    self.ib.connect('127.0.0.1', 7496, np.random.randint(0, 99999999))

        self.ib.cancelTickByTickData(self.main_instrument, 'Last')
        for additional_instrument in self.additional_data_sources:
            self.ib.cancelTickByTickData(additional_instrument.symbol, 'Last')

    def get_historical_data(self, contract: Contract, duration: str, bar_size: str, what_to_show: str):
        return self.ib.reqHistoricalData(
            contract,
            endDateTime='',
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow=what_to_show,
            useRTH=True,
            formatDate=1
        )

    def get_real_time_data(self, contract: Contract, generic_tick_list: str):
        return self.ib.reqMktData(
            contract,
            genericTickList=generic_tick_list,
            snapshot=False
        )

    def on_data(self, main_data):
        raise NotImplementedError("Strategy must implement on_data method")

    def calculate_exit_signals(self, main_data, additional_data):
        raise NotImplementedError("Strategy must implement calculate_signals method")

    def plot_price_with_signals(self, signals):
        raise NotImplementedError("Strategy must implement plot_price_with_signals method")

    def execute_entry_trades(self, signals, trade_size_long, trade_size_short):
        raise NotImplementedError("Strategy must implement execute_trades method")

    def execute_exit_trades(self, signals):
        raise NotImplementedError("Strategy must implement execute_trades method")

    @property
    def main_instrument(self):
        return self.config.symbol_config

    @property
    def additional_data_sources(self):
        return self.config.additional_data_sources_configs

    @property
    def strategy_name(self):
        return self.config.strategy_name

    @@property
    def contract(self):
        return Contract(self.main_instrument.symbol, self.main_instrument.exchange, self.main_instrument.secType, self.main_instrument.currency)

    @property
    def account_values(self):
        return self.ib.accountValues()

    @property
    def current_equity(self):
        return float(next((av.value for av in self.account_values if av.tag == 'NetLiquidation' and av.currency == 'USD'), None))

    @property
    def current_positions(self):
        return self.ib.positions()

    @property
    def open_trades(self):
        return self.ib.openTrades()

    def get_position_avg_price(self):
        positions = self.current_positions
        if len(positions) > 0:
            return (sum(pos.avgCost * pos.position for pos in self.current_positions) /
                      sum(pos.position for pos in self.current_positions))
        else:
            return 0


class TW_Strategy_v2(Strategy):
    def __init__(
            self,
            ib: IB,
            config: StrategyConfig,
            long_ok: bool = True,
            short_ok: bool = True,
            pyramid_limit: int = 3,
            scale_type: str = 'None',
            quant_trade_1: int = 60,
            quant_trade_2: int = 80,
            quant_trade_3: int = 100,
            useMA_long: bool = True,
            useMA_short: bool = True,
            wma_limit_input: int = 105,
            bars_limit_long: int = 98,
            bars_limit_short: int = 49,
            use_atr: bool = True,
            lr_length: int = 20,
            lr_offset: int = 4,
            use_vix: bool = True,
            vix_limit: float = 26.0,
            useSL: bool = True,
            LossPerc_long: float = 11.2,
            LossPerc_short: float = 5.2,
            useTP: bool = True,
            ProfitPerc_long: float = 11.2,
            ProfitPerc_short: float = 4.0,
            use_pdiff: bool = True,
            fast_length: int = 2,
            slow_length: int = 5,
            EMA1_length: int = 2,
            EMA2_length: int = 5,
            EMA3_length: int = 9,
            EMA4_length: int = 25,
            h: int = 11,
            rsiLengthInp: int = 6,
            maLengthInp1: int = 5,
            optim_sig_len: int = 9,
            tr_cross: int = 4,
    ):
        super().__init__(ib, config)
        self.long_ok = long_ok
        self.short_ok = short_ok
        self.pyramid_limit = pyramid_limit
        self.scale_type = scale_type
        self.quant_trade_1 = quant_trade_1
        self.quant_trade_2 = quant_trade_2
        self.quant_trade_3 = quant_trade_3
        self.useMA_long = useMA_long
        self.useMA_short = useMA_short
        self.wma_limit_input = wma_limit_input
        self.bars_limit_long = bars_limit_long
        self.bars_limit_short = bars_limit_short
        self.use_atr = use_atr
        self.lr_length = lr_length
        self.lr_offset = lr_offset
        self.use_vix = use_vix
        self.vix_limit = vix_limit
        self.useSL = useSL
        self.LossPerc_long = LossPerc_long
        self.LossPerc_short = LossPerc_short
        self.useTP = useTP
        self.ProfitPerc_long = ProfitPerc_long
        self.ProfitPerc_short = ProfitPerc_short
        self.use_pdiff = use_pdiff
        self.fast_length = fast_length
        self.slow_length = slow_length
        self.EMA1_length = EMA1_length
        self.EMA2_length = EMA2_length
        self.EMA3_length = EMA3_length
        self.EMA4_length = EMA4_length
        self.h = h
        self.rsiLengthInp = rsiLengthInp
        self.maLengthInp1 = maLengthInp1
        self.optim_sig_len = optim_sig_len
        self.tr_cross = tr_cross

    def on_data(self, main_data):
        # Get the historical data
        df_30 = self.get_historical_data(
            self.contract,
            duration='205 D',
            bar_size='30 min',
            what_to_show='TRADES'
        )
        df_90 = util.df(df_30).resample('90T').last().dropna()

        df_1D = self.get_historical_data(
            self.contract,
            duration='205 D',
            bar_size='1 D',
            what_to_show='TRADES'
        )
        df_1D = util.df(df_1D)

        df_3D = self.get_historical_data(
            self.contract,
            duration='205 D',
            bar_size='3 D',
            what_to_show='TRADES'
        )
        df_3D = util.df(df_3D)

        df_1dVIX = self.get_historical_data(
            Contract(symbol='VIX', exchange='CBOE', secType='IND', currency='USD'),
            duration='20 D',
            bar_size='1 D',
            what_to_show='TRADES',
        )
        df_1dVIX = util.df(df_1dVIX)

        # Calculate exit signals
        exit_signals = self.calculate_exit_signals(main_data)

        # Execute the exit trades
        self.execute_exit_trades(exit_signals)

        # Calculate the indicators/signals
        emacd_signals = self.calculate_emacd_signals(df_90)
        linreg_signals = self.calculate_linreg_signals(df_90, df_1D)
        momentum_signals = self.calculate_momentum_signals(df_90)
        atr_3d_filters = self.calculate_atr_filters(df_3D)
        vix_filters = self.calculate_vix_filters(df_1dVIX)

        strategy_signals = self.calculate_omega_signals(df_90, df_1D, df_3D)

        # Calculate entry sizes
        trade_multiplier = self.calculate_trade_multiplier(main_data)
        trade_size_long = (self.current_equity * trade_multiplier) / df_90['CLOSE'].iloc[-1]
        trade_size_short = (self.current_equity * self.quant_trade_1 / 100) / df_90['CLOSE'].iloc[-1]

        # Execute the trades
        self.execute_entry_trades(strategy_signals, trade_size_long, trade_size_short)

    def calculate_exit_signals(self, main_data, additional_data):
        pass

    def execute_exit_trades(self, signals):
        # Execute the trades
        pass

    def calculate_emacd_signals(self, historical_data):
        indicators = pd.DataFrame().reindex_like(historical_data)
        indicators['ema50'] = ta.ema(historical_data['CLOSE'], length=50)
        indicators['wma_limit'] = ta.wma(historical_data['CLOSE'], length=self.wma_limit_input)
        indicators['emacd'] = indicators['ema50'] - indicators['wma_limit']
        indicators['emacd_signal'] = ta.wma(indicators['emacd'], length=20)
        indicators['hist'] = indicators['emacd'] - indicators['emacd_signal']

        return indicators

    def calculate_linreg_signals(self, historical_data, daily_data):
        wma200 = ta.wma(daily_data['CLOSE'], length=200)
        closeD_under_wma200 = historical_data['CLOSE'] < daily_data['wma200'].iloc[-1]
        lr_close = ta.linreg(historical_data['CLOSE'], 5, 1)

        return lr_close

    def calculate_momentum_signals(self, historical_data):
        momentum = pd.DataFrame().reindex_like(historical_data)
        momentum['fast_ma'] = ta.ema(historical_data['CLOSE'], self.fast_length)
        momentum['slow_ma'] = ta.ema(historical_data['CLOSE'], self.slow_length)
        momentum['trend'] = momentum['fast_ma'] - momentum['slow_ma']
        momentum['EMA1'] = ta.ema(momentum['trend'], self.EMA1_length)
        momentum['EMA2'] = ta.ema(momentum['trend'], self.EMA2_length)
        momentum['EMA3'] = ta.ema(momentum['trend'], self.EMA3_length)
        momentum['EMA4'] = ta.ema(momentum['trend'], self.EMA4_length)
        momentum['LR2'] = ta.linreg(momentum['EMA2'], 7, 1)

        return momentum

    def calculate_atr_filters(self, historical_data):
        atr = pd.DataFrame().reindex_like(historical_data)
        atr['atr_3d'] = ta.atr(historical_data['HIGH'], historical_data['LOW'], historical_data['CLOSE'], 11)
        atr['atr_3d_signal'] = ta.linreg(atr['atr_3d'], length=self.lr_length, offset=self.lr_offset)
        atr['fast_ma_3d'] = ta.ema(historical_data['CLOSE'], length=self.fast_length)
        atr['slow_ma_3d'] = ta.ema(historical_data['CLOSE'], length=self.slow_length)
        atr['trend_3d'] = atr['fast_ma_3d'] - atr['slow_ma_3d']
        atr['EMA2_3d'] = ta.ema(atr['trend_3d'], length=self.EMA2_length)
        atr['LR2_3d'] = ta.linreg(atr['EMA2_3d'], length=7, offset=1)
        atr['ATR_long_yes'] = atr['atr_3d'] < atr['atr_3d_signal'] or atr['trend'] > atr['LR2_3d']
        atr['ATR_long_no'] = not atr['ATR_long_yes']

        return atr

    def calculate_omega_signals(self, df_90, df_1D, df_3D):
        df_90['h1'] = calculate_h1(df_90, self.h)
        df_90['rsi'] = ta.rsi(df_90['CLOSE'], length=self.rsiLengthInp)
        df_90['rsiMA1'] = ta.wma(df_90['CLOSE'], length=self.maLengthInp1)
        df_90['rsiMA1_smooth'] = ta.sma(df_90['rsiMA1'], length=3)

        df_90['rsiMA2'] = ta.wma(df_90['rsi'], length=6)
        df_90['rsiMA2_smooth'] = ta.sma(df_90['rsiMA2'], length=7)

        df_90['rsiMA3'] = ta.wma(df_90['rsi'], length=70)
        df_90['rsiMA3_smooth'] = ta.sma(df_90['rsiMA3'], length=7)

        df_90['rsiMA4'] = ta.wma(df_90['rsi'], length=5)

        # Linear regression calculations based on the first RSI MA
        df_90['reg_1'] = ta.linreg(df_90['rsiMA1'], length=self.optim_sig_len, offset=2)
        df_90['reg_2'] = ta.linreg(df_90['rsiMA1'], length=self.optim_sig_len + 2, offset=3)

        # Calculate the trigger value
        df_90['trigger'] = (df_90['rsi'] + df_90['rsiMA1']) / 2

        df_90['fast_ma'] = ta.ema(df_90['close'], fast_length)
        df_90['slow_ma'] = ta.ema(df_90['close'], slow_length)
        df_90['trend'] = df_90['fast_ma'] - df_90['slow_ma']
        df_90['EMA1'] = ta.ema(df_90['trend'], EMA1_length)
        df_90['EMA2'] = ta.ema(df_90['trend'], EMA2_length)
        df_90['EMA3'] = ta.ema(df_90['trend'], EMA3_length)
        df_90['EMA4'] = ta.ema(df_90['trend'], EMA4_length)
        # Calculate the Linear Regression Value of EMA2 with the length: 7, offset: 1
        df_90['LR2'] = ta.linreg(df_90['EMA2'], 7, 1)

    def calculate_vix_filters(self, vix_daily_data):
        return vix_daily_data['CLOSE'] > self.vix_limit

    def execute_entry_trades(self, signals, trade_size_long, trade_size_short):
        # Execute the trades
        long_cond = self.long_ok and signals['bull'] and (not self.use_atr or (self.use_atr and signals['ATR_long_yes']))
        if long_cond:
            self.enter_long_market(trade_size_long)

        short_cond0 = self.short_ok and signals['bear']
        short_cond1 = self.useMA_short and signals['wma_limit_yes']
        short_cond2 = signals['pdiff_above']
        short_cond = short_cond0 and (not self.use_vix or (self.use_vix and short_cond1)) and (not self.use_pdiff or (self.use_pdiff and short_cond2))
        if short_cond:
            self.enter_short_market(trade_size_short)

    def enter_long_market(self, trade_size_long: int):
        if self.ib.isConnected():
            if not isinstance(self.contract, Contract):
                raise ValueError("Invalid contract type. Expected Contract object.")
            order = Order(action='BUY', orderType='MKT', tif='GTC',
                          totalQuantity=trade_size_long)
            trade = self.ib.placeOrder(self.contract, order)
            return trade

        else:
            raise ConnectionError("IB is not connected.")

    def enter_short_market(self, trade_size_short: int):  # short ENTRY order
        if self.ib.isConnected():
            if not isinstance(self.contract, Contract):
                raise ValueError("Invalid contract type. Expected Contract object.")
            order = Order(action='SELL', orderType='MKT', tif='GTC',
                          totalQuantity=trade_size_short)
            trade = self.ib.placeOrder(self.contract, order)
            return trade
        else:
            raise ConnectionError("IB is not connected.")

    def calculate_trade_multiplier(self, main_data):
        scale_type = self.scale_type
        quant_trade_1 = self.quant_trade_1
        quant_trade_2 = self.quant_trade_2
        quant_trade_3 = self.quant_trade_3
        num_open_trades = len(self.open_trades)
        current_price = main_data.close
        position_avg_price = self.get_position_avg_price()

        if scale_type == "None":
            trade_multip = quant_trade_1 / 100
        elif scale_type == "Winners":
            if num_open_trades == 0 or current_price < position_avg_price:
                trade_multip = quant_trade_1 / 100
            elif num_open_trades == 1 and current_price > position_avg_price:
                trade_multip = quant_trade_2 / 100
            elif num_open_trades == 2 and current_price > position_avg_price:
                trade_multip = quant_trade_3 / 100
            else:
                trade_multip = quant_trade_1 / 100
        elif scale_type == "Losers":
            if num_open_trades == 0 or current_price > position_avg_price:
                trade_multip = quant_trade_1 / 100
            elif num_open_trades == 1 and current_price < position_avg_price:
                trade_multip = quant_trade_2 / 100
            elif num_open_trades == 2 and current_price < position_avg_price:
                trade_multip = quant_trade_3 / 100
            else:
                trade_multip = quant_trade_1 / 100
        else:  # scale_type is assumed to be "Both" or any other case
            if num_open_trades == 0:
                trade_multip = quant_trade_1 / 100
            elif num_open_trades == 1:
                trade_multip = quant_trade_2 / 100
            elif num_open_trades == 2:
                trade_multip = quant_trade_3 / 100
            else:
                trade_multip = None  # equivalent to 'na' in Pine Script

        return trade_multip
