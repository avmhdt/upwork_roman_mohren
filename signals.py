import pandas as pd
import pandas_ta as ta


long_cond = (signal7 or Stoch_BL_1 or buypoint_wpat or Stoch_BL2 or sig_2)
short_cond = and (Stoch_SL or sig_1 and plot_sig_7)

buy        =  long_cond and barstate.isconfirmed
sell       =  short_cond and barstate.isconfirmed
# ================= SIGNAL FOR STRATEGY =====================
Signal = 1 if buy else (-1 if sell else 0)
# plot(Signal: na, title = "💰OMEGA Signals", display = display.none)

class Signal(object):
    def __init__(self):
