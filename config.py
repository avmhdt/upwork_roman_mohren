from dataclasses import dataclass
from ib_insync import *
from typing import List


class Config(object):
    pass


class InstrumentBrokerConfig(Config):
    def __init__(self, symbol: str, exchange: str, currency: str, secType: str, primaryExchange: str = None):
        self._symbol = symbol
        self._exchange = exchange
        self._currency = currency
        self._secType = secType
        self._primaryExchange = primaryExchange

    @property
    def symbol(self):
        return self._symbol

    @property
    def exchange(self):
        return self._exchange

    @property
    def currency(self):
        return self._currency

    @property
    def secType(self):
        return self._secType

    @property
    def primaryExchange(self):
        return self._primaryExchange

    def __repr__(self):
        return f"Symbol: {self.symbol}, Exchange: {self.exchange}, Currency: {self.currency}, SecType: {self.secType}, PrimaryExchange: {self.primaryExchange}"


class StrategyConfig(Config):
    def __init__(
            self,
            ib_conn: IB,
            symbol_config: InstrumentBrokerConfig,
            additional_data_sources_configs: List[InstrumentBrokerConfig],
            strategy_name: str = None,
    ):
        self._ib_conn = ib_conn
        self._symbol_config = symbol_config
        self._additional_data_sources_configs = additional_data_sources_configs
        self._strategy_name = strategy_name

    @property
    def ib_conn(self):
        return self._ib_conn

    @property
    def symbol_config(self):
        return self._symbol_config

    @property
    def additional_data_sources_configs(self):
        return self._additional_data_sources_configs

    @property
    def strategy_name(self):
        return self._strategy_name

    def __repr__(self):
        return f"IB Connection: {self.ib_conn}, Symbol Configs: {self.symbol_config}, Additional Data Sources Configs: {self.additional_data_sources_configs}, Strategy Name: {self.strategy_name}"

