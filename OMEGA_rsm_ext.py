import math, datetime, pytz
import pandas as pd
# https:# github.com/twopirllc/pandas-ta/
import pandas_ta as ta
import pandas_datareader as pdr
import talib
import matplotlib.pyplot as plt
import numpy as np
from ib_insync import *

# =================== Functions ========================



# ========= Self-defined Technical Analysis Functions according to TradingView Cacls ===========

# def sma(x, y):
#     sum = 0.0
#     for i in range(y):
#         sum += x[i] / y
#     return sum
#
# def ema(src, length):
#     alpha = 2 / (length + 1)
#     ema = src[0]  # Initialize EMA with the first value of src
#     for price in src[1:]:  # Start from the second element
#         ema = alpha * price + (1 - alpha) * ema
#     return ema
#
# def wma(x, y):
#     norm = 0.0
#     sum = 0.0
#     for i in range(y):
#         weight = (y - i) * y
#         norm += weight
#         sum += x[i] * weight
#     return sum / norm
#
# def rma(src, length):
#     alpha = 1 / length
#     result = np.zeros_like(src)
#     result[0] = src[0]  # Initialize the first value of result as the first value of src
#     for i in range(1, len(src)):
#         result[i] = alpha * src[i] + (1 - alpha) * result[i - 1]
#     return result
#
# def rsi(prices, period):
#     # Calculate price differences
#     delta = prices.diff()
#
#     # Make two series: one for gains and one for losses
#     gain = (delta.where(delta > 0, 0)).fillna(0)
#     loss = (-delta.where(delta < 0, 0)).fillna(0)
#
#     # Calculate the Exponential Moving Average (EMA) of gains and losses
#     avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
#     avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
#
#     # Calculate the RS
#     rs = avg_gain / avg_loss
#
#     # Calculate the RSI
#     rsi = 100 - (100 / (1 + rs))
#
#     return rsi

# 1. Linreg version (from pandas_ta library)
# ta.linreg() # ta.linreg(source, period, offset)

# def stoch(close, high, low, length):
#     """
#     Calculate the stochastic oscillator %K line similar to Pine Script's ta.stoch() function.
#
#     Parameters:
#     close_prices (list or array): List or array of closing prices
#     high_prices (list or array): List or array of high prices
#     low_prices (list or array): List or array of low prices
#     length (int): The period over which to calculate the highs and lows
#
#     Returns:
#     np.array: Array of stochastic oscillator values
#     """
#     # Convert lists to numpy arrays if they aren't already
#     close = np.asarray(close)
#     high = np.asarray(high)
#     low = np.asarray(low)
#
#     # Initialize the result array
#     stoch_values = np.zeros_like(close)
#
#     # Calculate stochastic oscillator for each point
#     for i in range(length - 1, len(close)):
#         highest_high = np.max(high[i-length+1:i+1])
#         lowest_low = np.min(low[i-length+1:i+1])
#         stoch_values[i] = 100 * (close[i] - lowest_low) / (highest_high - lowest_low) if (highest_high - lowest_low) != 0 else 0
#
#     return stoch_values

pass
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

# Accessing specific data
open = df_90m['Open']
high = df_90m['High']
low = df_90m['Low']
close = df_90m['Close']


# ========== SIGNAL INPUTS ==============
# the bar progress calculation below (Pine Script) allows signals to be processed before the close of the current bar if
# if BarProgress4signal_input is < 100 (90 means 90% of the current bar needs to have passed for a signal to be allowed.

BarProgress4signal_input = 100 # = input.int(100, title="Live Bar Progress (in %)", minval=1, maxval=100, ...

TimeLeftInBar_signals_only = (barstate.isrealtime and (timenow - time) / 1000 > (
            timeframe.in_seconds() * (BarProgress4signal_input / 100))) or barstate.isconfirmed
 # if this feature is used then the strategy needs to be changed so that only one trade entry is allowed per bar.

# Hull Moving Average
h = 11
df_90m['h1'] = calculate_h1_h2(df_90m['close'], h)
# ta.hma()

# Relative Strength Index (RSI)
# User-defined inputs (these would be set up in the user interface)
rsiLengthInp = 6  # Lookback period for RSI
maLengthInp1 = 5  # Moving average length for the first MA
optim_sig_len = 9 # Length for linear regression signals
tr_cross = 4      # Lookback for crossunder signals

# Calculate RSI from the 'close' prices in df_90m DataFrame
df_90m['rsi'] = ta.rsi(df_90m['close'], length=rsiLengthInp)

# Calculate moving averages of RSI
df_90m['rsiMA1'] = ta.wma(df_90m['rsi'], length=maLengthInp1)
df_90m['rsiMA1_smooth'] = ta.sma(df_90m['rsiMA1'], length=3)

# Additional RSI MAs with different lengths
df_90m['rsiMA2'] = ta.wma(df_90m['rsi'], length=6)
df_90m['rsiMA2_smooth'] = ta.sma(df_90m['rsiMA2'], length=7)

df_90m['rsiMA3'] = ta.wma(df_90m['rsi'], length=70)
df_90m['rsiMA3_smooth'] = ta.sma(df_90m['rsiMA3'], length=7)

df_90m['rsiMA4'] = ta.wma(df_90m['rsi'], length=5)

# Linear regression calculations based on the first RSI MA
df_90m['reg_1'] = ta.linreg(df_90m['rsiMA1'], length=optim_sig_len, offset=2)
df_90m['reg_2'] = ta.linreg(df_90m['rsiMA1'], length=optim_sig_len + 2, offset=3)

# Calculate the trigger value
df_90m['trigger'] = (df_90m['rsi'] + df_90m['rsiMA1']) / 2

    # triggercol = rsi<rsiMA1 ? color.rgb(251, 125, 125) : color.rgb(50, 154, 251)

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

    # # EMA / SMA
    # EMAA1 = request.security(syminfo.tickerid, '30', ema(close, 175))
    # SMAA4 = sma(close, 20)
    #
    # # Trend identification
    # UPtrend = close > EMAA1
    # DOWNtrend = close < EMAA1

# Stochastic Section
# STOCH #1
periodK_1 = 14
smoothK_1 = 2
periodD_1= 2
df_90m['k'] = stoch(df_90m['close'], df_90m['high'], df_90m['low'], periodK_1)
df_90m['k_1'] = sma(df_90m['k'], smoothK_1)
df_90m['d_1'] = sma(df_90m['k_1'], periodD_1)

linreg0_period_k = 3
linreg0_offset_k = 1
df_90m['reg_k_1'] = linreg(df_90m['k'], linreg0_period_k, linreg0_offset_k)

# STOCH #2
periodK_2 = 35
smoothK_2 = 7
periodD_2= 3
df_90m['k_2'] = sma(stoch(df_90m['close'], df_90m['high'], df_90m['low'], periodK_1), smoothK_2)
df_90m['d_2'] = sma(df_90m['k_2'], periodD_2)

# ---STOCH #3
periodK_3 = 20
smoothK_3 = 2
periodD_3= 2
linreg1_period_D_3= 7
linreg1_offset_D_3= 1
linreg2_period_D_3= 13
linreg2_offset_D_3= 2
df_90m['k_3'] = ta.stoch(df_90m['close'], df_90m['high'], df_90m['low'], periodK_3)
df_90m['k_3_1'] = ta.sma(df_90m['k_3'], smoothK_3)
df_90m['d_3'] = ta.sma(df_90m['k_3'], periodD_3)
# Linear regression
df_90m['reg_d3_1'] = ta.linreg(df_90m['d_3'], length=linreg1_period_D_3, offset=linreg1_offset_D_3)
df_90m['reg_d3_2'] = ta.linreg(df_90m['d_3'], length=linreg2_period_D_3, offset=linreg2_offset_D_3)

# ---STOCH #4
periodK_4 = 50
smoothK_4 = 2
periodD_4= 2
df_90m['k_4'] = ta.stoch(df_90m['close'], df_90m['high'], df_90m['low'], periodK_4)
df_90m['k_4_1'] = ta.sma(df_90m['k_4'], smoothK_4)
df_90m['d_4'] = ta.sma(df_90m['k_4'], periodD_4)

# ---STOCH #5
periodK_5 = 100
smoothK_5 = 2
periodD_5= 2
df_90m['k_5'] = ta.stoch(df_90m['close'], df_90m['high'], df_90m['low'], periodK_5)
df_90m['k_5_1'] = ta.sma(df_90m['k_5'], smoothK_5)
df_90m['d_5'] = ta.sma(df_90m['k_5'], periodD_5)

# AVG Stochline -- Making an average of %D of both #1 and Stoch #2
df_90m['AVG_Stochline'] = (df_90m['d_1'] + df_90m['d_2']) / 2 - 3
period_Avg = 4
df_90m['AVG_EMA'] = ta.ema(df_90m['AVG_Stochline'], period_Avg)
df_90m['AVG_SMA'] = ta.sma(df_90m['AVG_Stochline'], period_Avg)
df_90m['SUM_k'] = (df_90m['k_1'] + df_90m['k_3'] + df_90m['k_4'] + df_90m['k_5']) / 4
df_90m['SUM1'] = (df_90m['k_3'] + df_90m['k_4'] + df_90m['k_5']) / 3
df_90m['SUM1_signal'] = ta.sma(ta.ema(df_90m['SUM1'], 7), 5)

# --- Moving Average on Stoch #2
MAlen = 12
MAsrc = df_09m['k_2']
MAoffset = 0
df_90m['MAout'] = ta.sma(MAsrc, MAlen)

# ========================= Trading Signals ==============================
# '▼'
# One
condreg = pivotlow(df_90m['reg_d3_2'],1,1)
signal7 = (df_90m['reg_d3_2']<65 and f_barssince(condreg,1)<10 and f_barssince(condreg,0)<1 and
           ta.valuewhen(condreg,df_90m['reg_d3_2'],1)<ta.valuewhen(condreg,df_90m['reg_d3_2'],0) and TimeLeftInBar_signals_only)

# Two
Stoch_BL_1 = (ta.crossover(df_0-m['k'],df_0-m['d_1']) and df_0-m['rsiMA1']<30 and df_90m['close']>df_90m['open'] and df_90m['MAout']<19) and TimeLeftInBar_signals_only


# ------ no DF accounted for below this


# Three
# Detect W-pattern at bottom is stochastic
Wpat = df['SUM_k'].shift(2) > df['SUM_k'].shift(1) and df['SUM_k'].shift(1) < df['SUM_k'] and df['SUM_k'].shift(1) < 6.7
# count_SUM_k = None
if Wpat:
    count_SUM_k = 0
else:
    count_SUM_k += 1
since_last_SUM_k = barssince(Wpat)
since_prev_SUM_k = valuewhen(Wpat, count_SUM_k[1], 0)
since_prev2_SUM_k = valuewhen(Wpat, count_SUM_k[1], 1)
buypoint_wpat = (SUM_k>SUM_k[1] and SUM_k[1]<SUM_k[2] and since_prev_SUM_k<8 and SUM_k[1]<30) and TimeLeftInBar_signals_only

# Four
linreg_sig5 = ta.linreg(close, 8, 5)
signal5 = (crossunder(reg_d3_1,reg_d3_2+.7) and reg_d3_2>58 and (close-ta.sma(close,50))>4 and
           close>linreg_sig5-0.5) and TimeLeftInBar_signals_only

    # ==================================
    # COUNT OMEGA BUY AND SELL SIGNALS
    # === INPUT SHOW PLOT ===
    # i_show = input(defval = false, title = "Show Buy & Sell Signals Count?", tooltip = "This will only count the signals that are actually plotting, which can be turned on or off above.")
    # # === INPUT BACKTEST RANGE ===
    # i_from = input.time(defval = timestamp("01 Jan 2000 00:00 +0000"), title = "Begin Count here:")
    # i_thru = input.time(defval = timestamp("01 Jan 2035 00:00 +0000"), title = "End Count here:")
    # # === FUNCTION EXAMPLE ===
    # def date():
    #     time >= i_from and time <= i_thru  # create date function 'within window of time'

# Sending Trading Signals to the Strategy Logic for final filtering
long_cond = date() and (signal7 or Stoch_BL_1 or buypoint_wpat or Stoch_BL2 or sig_2)
short_cond = date () and (Stoch_SL or sig_1 and plot_sig_7)

buy        =  long_cond and barstate.isconfirmed
sell       =  short_cond and barstate.isconfirmed
# ================= SIGNAL FOR STRATEGY =====================
Signal = 1 if buy else (-1 if sell else 0)
# plot(Signal: na, title = "💰OMEGA Signals", display = display.none)



