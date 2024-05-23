import pandas as pd
import pandas_ta as ta
import talib
import numpy as np


def calculate_h1(df, h):
    def wma(values, n):
        weights = np.arange(1, n + 1)
        return np.dot(values, weights) / weights.sum()

    h2ma = df['close'].rolling(window=round(h / 2), min_periods=1).apply(lambda x: wma(x, len(x)), raw=True)
    hma = df['close'].rolling(window=h, min_periods=1).apply(lambda x: wma(x, len(x)), raw=True)
    diff = h2ma - hma

    sqh = round(np.sqrt(h))

    h1 = diff.rolling(window=sqh, min_periods=1).apply(lambda x: wma(x, len(x)), raw=True)
    h2 = diff.shift(1).rolling(window=sqh, min_periods=1).apply(lambda x: wma(x, len(x)), raw=True)

    df['h1'] = h1
    # df['h2'] = h2
    # df['color'] = np.where(h1 > h2, '#5fb5fb', '#66686d')

    return df['h1']


def pivotlow(data, left_span, right_span):
    """
    Identify pivot lows in a list of data points.

    Parameters:
    data (list or array): Time series data.
    left_span (int): Number of bars to the left to compare.
    right_span (int): Number of bars to the right to compare.

    Returns:
    list: Indices of the pivot lows.
    """
    pivot_lows = []
    for i in range(left_span, len(data) - right_span):
        is_pivot_low = all(data[i] < data[j] for j in range(i - left_span, i)) and \
                       all(data[i] < data[j] for j in range(i + 1, i + right_span + 1))
        if is_pivot_low:
            pivot_lows.append(i)
    return pivot_lows if pivot_lows else None


def pivothigh(data, left_span, right_span):
    """
    Identify pivot highs in a list of data points.

    Parameters:
    data (list or array): Time series data.
    left_span (int): Number of bars to the left to compare.
    right_span (int): Number of bars to the right to compare.

    Returns:
    list or None: Indices of the pivot highs or None if no pivot highs are found.
    """
    pivot_highs = []
    for i in range(left_span, len(data) - right_span):
        is_pivot_high = all(data[i] > data[j] for j in range(i - left_span, i)) and \
                        all(data[i] > data[j] for j in range(i + 1, i + right_span + 1))
        if is_pivot_high:
            pivot_highs.append(i)
    return pivot_highs if pivot_highs else None
