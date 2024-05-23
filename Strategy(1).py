
# Implement Reconciliation / Exception Handling
# - Check IB TWS connection status using app.isConnected() method on every iteration of the run, typically based on your trading frequency (e.g., every 5 mins).
# - Implement another check for internet connection by pinging your broker's server or any public website.
# - Set up a loop to continuously check for restored connection if no response is received from the ping command.
# - Run the connection check loop with a specified interval.
# - Upon reconnection:
#   - Check for all open positions in the account and adjust positions in your algorithm if necessary.
#   - Fetch historical data for the duration of the disconnection to ensure accurate technical or statistical indicators.
#   - Reset streaming data by canceling current subscriptions and resubscribing.

# IMPORTS
#import tradingw999 / MomAlgo / 1 as momal
from datetime import datetime
from ib_insync import *
#util.startLoop()  # only use in interactive environments (i.e. Jupyter Notebooks)
ib = IB()
ib.connect(host='127.0.0.1', port=7497, clientId=1)

# Exchange trading hours for CST
exchange_time = datetime.now(pytz.timezone('US/Central'))
exchange_close = exchange_time.replace(hour=15, minute=0, second=0).strftime("%Y%m%d %H:%M:%S")

# ===================================
# Import Updated Strategy Inputs from the Django StrategyApp
from .models import StrategySettings

def update_strategy_settings():
    """
    Update the strategy settings based on the retrieved settings from the database.
    """
    # Retrieve the strategy settings from the database
    strategy_settings = StrategySettings.objects.first()

    # Return an error if strategy_settings doesn't exist
    if not strategy_settings:
        raise ValueError("Strategy settings not found.")

    # Update the necessary variables or function calls based on the retrieved settings
    default_values = {
        'DateFilter': False,
        'start_time': "1 1 2018 08:30",
        'end_time': "1 1 2029 15:00",
        'long_ok': True,
        'short_ok': True,
        'pyramid_limit': 3,
        'scale_type': "None",
        'quant_trade_1': 60,
        'quant_trade_2': 80,
        'quant_trade_3': 100,
        'useMA_long': True,
        'useMA_short': True,
        'wma_limit_inp': 105,
        'bars_limit_long': 98,
        'bars_limit_short': 49,
        'use_atr': True,
        'lr_length': 20,
        'lr_offset': 4,
        'use_vix': True,
        'vix_limit': 26,
        'useSL': True,
        'lossPerc_long': 11.2,
        'lossPerc_short': 5.2,
        'useTP': True,
        'profitPerc_long': 11.2,
        'profitPerc_short': 4
    }

    # Check if any settings need to be updated
    updated_settings = False
    for var_name, default_value in default_values.items():
        if getattr(strategy_settings, var_name) != default_value:
            setattr(update_strategy_settings, var_name, getattr(strategy_settings, var_name))
            updated_settings = True

    # Return any necessary values or indicate success
    if updated_settings:
        return strategy_settings
    else:
        return None
update_strategy_settings()

# ======================================
# CONTRACT INFO
# Define contracts
symbol = 'SPY'
contract = Stock(symbol, 'SMART/AMEX', 'USD')
vix_contract = Stock('SPY', 'SMART/AMEX', 'USD')
    # spxl_contract = Stock('SPXL', 'SMART', 'USD')
    # soxl_contract = Stock('SOXL', 'SMART', 'USD')
# data_spy_chart = ib.reqMktData(contract) # request a tick data stream
# data_spy_chart.marketPrice() # view the current price by calling the marketPrice function

# =============== Get DATA from IBKR ========================
dt = ''
barsList = []
while True:
    bars = ib.reqHistoricalData(
        contract,
        endDateTime=dt,
        durationStr='205 D',
        barSizeSetting='30 mins',  # Changed from '90 min' to '30 mins'
        whatToShow='TRADES',
        useRTH=True,
        formatDate=1)
    if not bars:
        break
    barsList.append(bars)
    dt = bars[0].date
# Convert all collected data to DataFrame
df = util.df(barsList)

# ===== CHART TIME FRAME DATA for 90m, 1d, 3d =====
# Resample 30-minute bars to 90-minute bars, because everything runs on 90-minute bars (this is also true for the OMEGA Signals
df.set_index('date', inplace=True)  # Ensure 'date' is the index for resampling
df_90m = df.resample('90T').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
})

# Get --OTHER CHART TIMEFRAME-- DATA
# Request historical data for the SPY contract for 1D bars
dt_1D = ''
barsList_1D = []
while True:
    bars_1D = ib.reqHistoricalData(
        contract,
        endDateTime=dt_1D,
        durationStr='205 D',
        barSizeSetting='1 D',
        whatToShow='TRADES',
        useRTH=True,
        formatDate=1)
    if not bars_1D:
        break
    barsList_1D.extend(bars_1D)  # Use extend to add all bars from the list
    dt_1D = bars_1D[0].date
df_1D = util.df(barsList_1D)  # Create DataFrame from the complete list of bars

# Request historical data for the SPY contract for 3-day bars
dt_3D = ''
barsList_3D = []
while True:
    bars_3D = ib.reqHistoricalData(
        contract,
        endDateTime=dt_3D,
        durationStr='205 D',
        barSizeSetting='3 D',
        whatToShow='TRADES',
        useRTH=True,
        formatDate=1)
    if not bars_3D:
        break
    barsList_3D.extend(bars_3D)  # Use extend to add all bars from the list
    dt_3D = bars_3D[0].date
df_3D = util.df(barsList_3D)  # Create DataFrame from the complete list of bars

# VIX data: Fetch the most recent fully completed 1-day bar close
while True:
    bars = ib.reqHistoricalData(
        vix_contract,
        endDateTime=dt,
        durationStr='20 D',  # Fetch data for one day
        barSizeSetting='1 day',  # Set bar size to 1 day
        whatToShow='TRADES',
        useRTH=True,
        formatDate=1)
    if not bars:
        break
    barsList.append(bars)
    dt = bars[0].date
# Convert the collected data to DataFrame
df_1dVIX = util.df(barsList)


# ============= STRATEGY INPUTS ==============

# Get Source Data / Indicator buy & sell values from OMEGA Signals
ext_source_ = input.source(close, title="Data source", group=group_7)
ext_source = nz(ext_source_)
# 1 is bull signal
bull = (ext_source == 1)
# -1 is bear signal
bear = (ext_source == -1)
# Entry Price
entry_price = valuewhen(condition=bear or bull, source=close, occurrence=0)

# Set Strategy Execution Date Range and on/off box
use_date_filter = True
start_time = datetime.strptime("6 May 2024 08:30", "%d %b %Y %H:%M")
end_time = datetime.strptime("30 Dec 2035 17:00", "%d %b %Y %H:%M")

def trade_in_date_range(use_date_filter, start_time, end_time):
    """
    Check if the current time falls within the specified date range.

    Parameters:
    - use_date_filter (bool): Flag indicating whether to use the date filter.
    - start_time (datetime): The start time of the date range.
    - end_time (datetime): The end time of the date range.

    Returns:
    - bool: True if the current time falls within the date range, False otherwise.
    """
    if not isinstance(use_date_filter, bool):
        return "Invalid input: use_date_filter must be a boolean value."
    if not isinstance(start_time, datetime):
        return "Invalid input: start_time must be a datetime object."
    if not isinstance(end_time, datetime):
        return "Invalid input: end_time must be a datetime object."
    
    if use_date_filter:
        return start_time <= datetime.utcnow() <= end_time
    else:
        return False

# >>>>>>>>> Strategy Directions & Scaling/Leverage <<<<<<<<<<"
long_ok = True      # this should be an input
short_ok = True     # this should be an input
pyramid_limit = 3   # this should be an input
scale_type = 'None' # this should be an input (see options below)
# input.string("Both", title="Scale Longs into Winners, Losers or Both?",
#                           options=["Winners", "Losers", "Both"],
#                           tooltip="You can use this settings to scale into long positions only at this time.\n\nYou can"
#                                   " choose to scale into losing longs, winning longs, or both.\n\nIf you want to use "
#                                   "leverage(use > 100 % of equity), then your combined percentages for 1st, 2nd, and "
#                                   "3rd Long can go over 100. If you don't want to use leverage then all three together "
#                                   "should not be higher than 100.")
quant_trade_1 = 60  # this should be an input (Pyramid Trade #1)
quant_trade_2 = 80  # this should be an input (Pyramid Trade #2)
quant_trade_3 = 100 # this should be an input (Pyramid Trade #3)

# EMA to reduce LONG EXITS (filters out short signals that would exit long trades, and enable more SHORT ENTRIES
# "Stay in Long Trades Longer"
useMA_long = True        # this should be an input field, tooltip="This enables that long positions can only be exited with short signals when the current WMA"
                    #         " is lower than on the previous bar/candle.")
useMA_short = True
wma_limit_inp = 105

# Limit Length of Trades based on # of candles
# var group_6 = "Max Length of Trades in # of Candles"
bars_limit_long = 98     # this should be an input = input.int(78, title="Limit of # Bars in a Trade", group=group_6,
                    # tooltip="This defines the maximum number of candles / bars that a trade can have before being "
                    #         "exited. If you want this to be irrelevant, put it to 1000 or higher.")
bars_limit_short = 49

# ===============================================
# ---- Scaling / Pyramiding into Long losers / winners / both / none
# Get the number of open trades and the average position price
pos = ib.positions()                # IB_insync function
open_trades = len(ib.positions())   # IB_insync function
position_avg_price = (sum(pos.avgCost * pos.position for pos in ib.positions()) /
                      sum(pos.position for pos in ib.positions())) if ib.positions() else 0
positions_avg_price
# Calculate trade multiplier for LONG trades only
def calculate_trade_multiplier(num_open_trades, current_price, position_avg_price, scale_type, quant_trade_1,
                               quant_trade_2, quant_trade_3):
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

calculate_trade_multiplier(open_trades, current_price, position_avg_price, scale_type, quant_trade_1, quant_trade_2,
                           quant_trade_3)

# Request account values
account_values = ib.accountValues(account='account #1')
# Filter for the current account value in USD
current_equity = next((av.value for av in account_values if av.tag == 'NetLiquidation' and av.currency == 'USD'), None)
trade_size_long = (current_equity * trade_multip) / close
trade_size_short = (current_equity * quant_trade_1 / 100) / close

# # other examples
# avs = ib.accountValues()
# for i in range(len(avs)):
#     if avs[i].tag == "NetLiquidation":
#         print(avs[i])
#     elif avs[i].tag == "UnrealizedPnL" and avs[i].currency == "BASE":
#         print(avs[i])

# ======================================
# GET HISTORICAL DATA --- Code examples
# historical_data_spy = ib.reqHistoricalData(     # IB_insync function
#     contract_contract,
#     '',
#     barSizeSetting='90 mins',
#     durationStr='3 M',
#     whatToShow='TRADES',
#     useRTH=True
#     )
#
# historical_data_spy[-1].open # get open price of most the current bar
# util.df(historical_data_spy) # create dataframe from the bar/candle data (IB_insync function)

# ============= DATA CALCS ==============
# EMA_CD
df_90['ema50'] = ta.wma(df_90m['close'], 50)
df_90['wma_limit'] = ta.wma(df_90m['close'], wma_limit_inp)
df_90['emacd'] = df_90['ema50'] - df_90['wma_limit']
df_90['emacd_signal'] = ta.wma(df_90['emacd'], 20)
df_90['hist'] = df_90['emacd'] - df_90['emacd_signal']

# Calculate the 200-period wma of 1-day closes
df_1D['wma200'] = df_1D['close'].ta.wma(length=200)

# close_D_under200MA is true when close < other200 is true
df_90m['close_D_under200MA'] = df_90m['close'] < df_1D['wma200'].iloc[-1]  # Compare df_90m with the last value of wma200 from df_1D
                                                                 #
# Linreg of chart timeframe bars close prices (length: 5, offset: 1)
df_90m['lr_close'] = ta.linreg(df_90m['close'], 5, 1)

# Momentum Section
# Inputs
fast_length = 2
slow_length = 5
EMA1_length = 2
EMA2_length = 5
EMA3_length = 9
EMA4_length = 25
# Monentum Calcs
df_90m['fast_ma'] = ta.ema(df_90m['close'], fast_length)
df_90m['slow_ma'] = ta.ema(df_90m['close'], slow_length)
df_90m['trend'] = df_90m['fast_ma'] - df_90m['slow_ma']
df_90m['EMA1'] = ta.ema(df_90m['trend'], EMA1_length)
df_90m['EMA2'] = ta.ema(df_90m['trend'], EMA2_length)
df_90m['EMA3'] = ta.ema(df_90m['trend'], EMA3_length)
df_90m['EMA4'] = ta.ema(df_90m['trend'], EMA4_length)
# Calculate the Linear Regression Value of EMA2 with the length: 7, offset: 1
df_90m['LR2'] = ta.linreg(df_90m['EMA2'], 7, 1)

# =============================================
# ---- ATR & VIX Filter
# "Market Volatility Risk Adjustment Settings - ATR & VIX"
use_atr = True      # this should be an input = get_input("Use ATR to Limit Long Entries? (True/False)", True, bool)
lr_length = 20      # this should be an input = get_input("ATR Length", 20, int)
lr_offset = 4       # this should be an input = get_input("ATR Offset", 4, int)

# - Calculate the ATR with each bar representing 3 trading days, over 11 bars
df_3D['atr_3d'] = ta.atr(df_3D['High'], df_3D['Low'], df_3D['Close'], length=11)
# Calculate the 3-day ATR signal (linear regression)
df_3D['atr_3d_signal'] = ta.linreg(df_3D['atr_3d'], length=lr_length, offset=lr_offset)

# - Get 3-day Trend Momentum data
    # (Pine Script) trend_3d = request.security(syminfo.tickerid, "3D", trend)
# Calculate 'trend' on the resampled data
df_3D['fast_ma_3d'] = ta.ema(df_3D['close'], length=fast_length)
df_3D['slow_ma_3d'] = ta.ema(df_3D['close'], length=slow_length)
df_3D['trend_3d'] = df_3D['fast_ma_3d'] - df_3D['slow_ma_3d']

# Get 3-day LR2 (linear regression on EMA2 of Momentum 'trend')
df_3D['EMA2_3d'] = ta.ema(df_3D['trend_3d'], length=EMA2_length)
df_3D['LR2_3d'] = ta.linreg(df_3D['EMA2_3d'], length=7, offset=1)

# - Exclude signals from trading based on ATR activity and Trend Momentum
ATR_long_yes = df_3D['ATR'] < df_3D['atr_3d_signal'] or df_3D['trend'] > df_3D['LR2_3d']
ATR_long_no = not ATR_long_yes
# DEBUG
# bgcolor(ATR_long_yes ? color.rgb(76, 175, 79, 63): color.rgb(255, 235, 59, 100))

# - Daily VIX
# Extract the close of the most recent fully completed 1-day bar of VIX
Current_1d_VIX = df_1dVIX['close'].iloc[-1] # non-repainting 1-day VIX
use_vix = True      # this should be an input = input.bool(true, "Use Vix to Limit Short Entries?", tooltip="VIX settings are used for SHORT trades only. Define the Zone of VIX required to engage in short trades. If you set this to 0 then short trades aren't impacted by this setting.")
vix_limit = 26      # this should be an input = input.float(defval=26, title="(SHORT side) Vix - Lower Limit", step=0.1)
vix_D_above = Current_1d_VIX > vix_limit

# ===============================================
# ---- SL an TP Settings

# -- Stop-Loss
# var group_3 = ">>>>>>>>> Stop-Loss Settings <<<<<<<<<<"
useSL = True        # this should be an input = input.bool(true, title="Stop-Loss", group=group_3, inline='sl')
LossPerc_long = 11.2 # this should be an input = input.float(11.2, title="Long %", minval=0.0, step=0.1, group=group_3, inline='sl') / 100
LossPerc_short = 5.2 # this should be an input = input.float(5.2, title="Short %", minval=0.0, step=0.1, group=group_3, inline='sl') / 100
final_SL_Long = strategy.position_avg_price * (1 - LossPerc_long)
final_SL_Short = strategy.position_avg_price * (1 + LossPerc_short)

# -- Take-Profit
# var group_4 = ">>>>>>>>> Take Profit Settings <<<<<<<<<<"
useTP = True        # this should be an input = input.bool(true, title="Take-Profit", group=group_4, inline='tp')
ProfitPerc_long = 11.2 # this should be an input = input.float(11.2, title="Long %", minval=0.0, step=0.1, group=group_4, inline='tp') / 100
ProfitPerc_short = 4.0 # this should be an input = input.float(4, title="Short %", minval=0.0, step=0.1, group=group_4, inline='tp') / 100
TPlongPrice = strategy.position_avg_price * (1 + ProfitPerc_long)
TPshortPrice = strategy.position_avg_price * (1 - ProfitPerc_short)

# ===============================================

# ORDERS: specify & execute
def enter_long_market(contract, trade_size_long): # long ENTRY order
    if ib.isConnected():
        if not isinstance(contract, Contract):
            raise ValueError("Invalid contract type. Expected Contract object.")
        order = Order(action='BUY', orderType='MKT', tif='GTC', totalQuantity=trade_size_long)   # IB_insync data class
        trade = ib.placeOrder(contract, order)
        return trade
    else:
        ???????

def enter_short_market(contract, trade_size_short): # short ENTRY order
    if ib.isConnected():
        if not isinstance(contract, Contract):
            raise ValueError("Invalid contract type. Expected Contract object.")
        order = Order(action='SELL', orderType='MKT', tif='GTC', totalQuantity=trade_size_short)  # IB_insync data class
        trade = ib.placeOrder(contract, order)
        return trade
    else:
        ???????

def exit_short_market(contract): # Short Exit order
    if ib.isConnected():
        if not isinstance(contract, Contract):
            raise ValueError("Invalid contract type. Expected Contract object.")
        order = Order(action='BUY', orderType='MKT', tif='GTC', totalQuantity=-position.position) # IB_insync data class
        trade = ib.placeOrder(contract, order)
    else:
        ???????

def exit_long_market(contract):  # Long Exit order
    if ib.isConnected():
        if not isinstance(contract, Contract):
            raise ValueError("Invalid contract type. Expected Contract object.")
        order = Order(action='Sell', orderType='MKT', tif='GTC', totalQuantity=position.position) # IB_insync data class
        trade = ib.placeOrder(contract, order)                                                    # IB_insync function
    else:
        ???????

# ==========================================
# --------- ORDER SYSTEM
# Check for OPEN POSITIONS
open_positions = ib.positions()         # IB_insync function

# ---- STRATEGY EXITS
# -- On-Opposite Exit

# Close long position
if position_size > 0 and bear and useMA_long and df_90m['wma_limit'].iloc[-1] <= df_90m['wma_limit'].iloc[-2]:
    exit_long_market(contract)
    # print(f"EXIT LONG {contract.symbol}, price = {df['close'].iloc[-1]}")
if position_size > 0 and bear and not useMA_long:
    exit_long_market(contract)
    # print(f"EXIT LONG {contract.symbol}, price = {df['close'].iloc[-1]}")

# Close short position
if position_size < 0 and bull:
    exit_short_market(contract)
    # print(f"EXIT SHORT {contract.symbol}, price = {df['close'].iloc[-1]}")

# -- Exit trades based on number of bars (if bars since entry == bars limit, exit trade)
    # ~~~~~~~~~~~ THIS HAS NOT YET BEEN CONVERTED TO PYTHON ~~~~~~~~~~~~

# bars_since__first_entry() = bar_index - strategy.opentrades.entry_bar_index(0)
    # Assuming 'current_bar_index' is the index of the current bar
    # and 'entry_bar_index' is the index of the bar at which the first trade was entered
def bars_since_first_entry(current_bar_index, entry_bar_index):
    return current_bar_index - entry_bar_index
# Calculate bars since first entry
result = bars_since_first_entry(current_bar_index, entry_bar_index)
    # print("Bars since first entry:", result)

if position.position > 0 and BarsSinceFirstEntry() == bars_limit_long: # close long position if the bars_limit_long has been reached
    for position in positions:
        if position.contract.symbol == symbol:
            # Position is long, place a SELL order
            exit_long_market(contract)

if position.position < 0 and BarsSinceFirstEntry() == bars_limit_short: # close short position if the bars_limit_short has been reached
    for position in positions:
        if position.contract.symbol == symbol:
            # Position is short, place a SELL order
            exit_short_market(contract)

# -- Stop-Loss and Take-Profit Exits
if position.position > 0:
    if useSL and final_SL_Long: # use stop-loss? = true AND final_SL_Long price is reached
        exit_long_market(contract)
    elif useTP and TPlongPrice: # use take-profit? = true AND TPlongPrice price is reached
        exit_long_market(contract)
if strategy.position_size < 0:
    if useSL and final_SL_Short: # use stop-loss? = true AND final_SL_Long price is reached
        exit_short_market(contract)
    elif useTP and TPshortPrice:# use take-profit? = true AND TPshortPrice price is reached
        exit_short_market(contract)

# ======================================
# ---- STRATEGY ENTRIES
# -- Long Entry
if use_atr:
    if long_ok and TradeInDateRange() and bull and ATR_long_yes:
        enter_long_market(contract, trade_size_long)
    elif long_ok and TradeInDateRange() and bull:
        enter_long_market(contract, trade_size_long)

# -- Short Entry
if short_ok and TradeInDateRange() and bear and (use_vix or (useMA_short and (df_90m['wma_limit'].iloc[-1] <=
                                                                              df_90m['wma_limit'].iloc[-2]))):
    # Enter short on new bar entry IF daterange=true and bear signal==yes, and (use_vix==true or (useMA_short==true
    # and wma_limit went down the last bar)
    enter_short_market(contract, trade_size_short)
elif short_ok and TradeInDateRange() and bear and use_pdiff and pdiff_above:
    enter_short_market(contract, trade_size_short)
elif short_ok and TradeInDateRange() and bear:
    enter_short_market(contract, trade_size_short)
# =====================================
