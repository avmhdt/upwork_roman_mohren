import pandas as pd
import numpy as np
import pandas_ta as ta
import talib
from signals import Signal
from ib_insync import *

from .config import StrategyConfig
from .signals import Signal


class Strategy(object):
    def __init__(self, ib: IB, config: StrategyConfig):
        self.ib = ib
        self.config = config

    def run(self):
        # while receiving real time data, call on_data method



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

    def on_data(self, data):
        raise NotImplementedError("Strategy must implement on_data method")

    @property
    def main_instrument(self):
        return self.config.symbol_config

    @property
    def additional_data_sources(self):
        return self.config.additional_data_sources_configs

    @property
    def strategy_name(self):
        return self.config.strategy_name


class TW_Strategy_v2(Strategy):
