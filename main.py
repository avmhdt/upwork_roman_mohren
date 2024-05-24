import pandas as pd
import os
import numpy as np
import sys
from ib_insync import *
from config import StrategyConfig, InstrumentBrokerConfig
from strategy import Strategy


if __name__ == '__main__':

    ib = IB()
    ib.connect('127.0.0.1', 7496, np.random.randint(0, 99999999))
    ib.reqMarketDataType(1)

    SPY_CONFIG = InstrumentBrokerConfig(
        symbol='SPY',
        exchange='SMART',
        currency='USD',
        secType='STK',
        primaryExchange='ARCA'
    )
    SOXL_CONFIG = InstrumentBrokerConfig(
        symbol='SOXL',
        exchange='SMART',
        currency='USD',
        secType='STK',
        primaryExchange='ARCA'
    )

    x_TW_Config_v2 = StrategyConfig(
        ib_conn=ib,
        symbol_config=SPY_CONFIG,
        additional_data_sources_configs=[SOXL_CONFIG],
        strategy_name='TW_Strategy_v2',
    )

    # Load the strategy
    x_TW_Strategy_v2 = Strategy(ib, x_TW_Config_v2)

    # Start the strategy
    x_TW_Strategy_v2.run()

    # Disconnect
    ib.disconnect()





