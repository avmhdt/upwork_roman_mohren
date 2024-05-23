import numpy as np
import pandas as pd


def crossover(series1, series2):
    """Return True if series1 crosses over series2 in the most recent completed bar."""
    # Check the condition for the last element in the series
    crossed_over = (series1.iloc[-2] < series2.iloc[-2]) and (series1.iloc[-1] > series2.iloc[-1])
    return crossed_over


def crossunder(series1, series2):
    """Return True if series1 crosses over series2 in the most recent completed bar."""
    # Check the condition for the last element in the series
    crossed_under = (series1.iloc[-2] > series2.iloc[-2]) and (series1.iloc[-1] < series2.iloc[-1])
    return crossed_under


def valuewhen(condition, series, nth_occurrence):
    """Return the Value of Series the nth last time condition was true"""
    # Validate inputs
    if not (len(condition) == len(series)):
        raise ValueError("Condition and series must be of the same length")

    # Find indices where condition is True
    true_indices = [index for index, cond in enumerate(condition) if cond]

    # Check if nth_occurrence is within the range of true occurrences
    if nth_occurrence >= len(true_indices):
        raise IndexError("nth_occurrence is out of range of true conditions")

    # Calculate the index for the nth last occurrence
    target_index = true_indices[-(nth_occurrence + 1)]

    # Return the corresponding value from series
    return series[target_index]

    # print(valuewhen(condition, series, nth_occurrence))  # Output should be 40


def barssince(condition):
    """
    Returns the number of bars back since the condition has occurred last.

    :param conditions: List of boolean values, where each value indicates whether the condition was met.
    :return: Number of bars since the condition last occurred. Returns None if the condition never met.
    """
    try:
        # Reverse the list to find the last occurrence from the end of the list
        reversed_condition = condition[::-1]
        # Find the index of the last True value
        index = reversed_condition.index(True)
        return index
    except ValueError:
        # Return None if True is not found in the list
        return None


def f_barssince(cond, count):
    # Convert condition array to numpy array for processing
    cond_array = np.array(cond)
    # Find indices where condition is True
    true_indices = np.where(cond_array)[0]

    # Check if we have enough true conditions to get the 'count' instance
    if len(true_indices) > count:
        # Get the index of the 'count' instance of condition being True
        target_index = true_indices[-(count + 1)]
    else:
        # If not enough instances, return None or handle as needed
        return None

    # Calculate bars since the condition was True 'count' times ago
    barssince = len(cond_array) - 1 - target_index
    return barssince

