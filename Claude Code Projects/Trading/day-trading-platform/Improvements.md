This Day Trading Platform program is working pretty good but I need 
your help to implement the following changes:

1. Break Strategy up into separate Entry and Exit strategies and make them selectable and independent of each other.  For example, an Entry can be executed based on VWAP but the Exit can be executed based on MACD.
2. Make Trading Interval selectable depends on whether I want to Day Trade, Swing Trade or Postition Trade Day Trade Entries and Exits should trigger off the closing bar of 5 min chart, Swing Trade Entries and Exits should be triggered off the closing bar of the 1 hour chart and Position Trade Entries and Exits should be triggered off closing bar of the Daily chart.
3. Allow only maximum one trade per day (Entry or Exit) for Swing Trades and Position Trades.  Allow maximum two trades per day (one Entry and one Exit) for Day Trades.  If no Exit condition for Day Trade were met at the end of the day, exit trade automatically at the end of the day.
4. Make porfolio position sizing simpler.  Each Trading Interval will be executed on 1/3 of total porfolio.  Rebalance weighting after each exit.
5.  Allow user to input stock symbols, not a limitted number of pre-determined stocks.
6.  News section is not working.  Fix it.

* Ask Claude to add trailing stops (combine a % trailing stop and a strategy stop)
______________________________________

For Daytrading, if the Entry condition triggers, I would like a 1/3 of the porfolio go into the trade and exit the whole entire position via the combined trailing stop or at the end of the day. i.e. if an Entry exists on a day, the whole position must be closed on that day.  For the Recent Signal table, I want a column to post profit/loss immediate on every entry/exit pair.

_________________________________________


Make sure that chart is adjusted for splits and reverse splits.
Add a column for transaction value in dollars.

Ask me any question if you are unsure before proceeding.

________________________________________________

Adjust the program to make it simpler.  Only implement Day Trading part of program.  For the ORB strategy, the opening range should be fixed at 30 minutes.  Add one column next to the exit column to indicate whether the position is stopped out by the Strategy Stop, the Fixed trailing stop or by the end of the day.

_________________________________________________

Add the following user-defined exit strategies:

1.  orb_user_entry

This user-defined entry strategy should only be applied on very strong trend days. This is executed on both Long and Short sides of the market.  On a very strong up trend day (Long Entry), volume should increase as price break out of the opening range.  This is marked by a closing of a 5 minute bar higher than the opening range price.  Similarly, on a very strong down trend day (Short Entry), volume should also increase as price break down from the opening range price.  This is marked by a closing of a 5 minute bar lower than the opening range.  The volume multiple limit for entry should be selectable from 1.25 to 2.0 (defaulted to 1.5) times that of the average volume of the first 30 minutes (the opening period).  This strategy should not be executed outside the 1.5-hour window of market's open (after 8:00 PST, this entry is no longer available).  

* This can also be combined with other indicators such as MACD or RSI for more assurance.

2.  orb_reversal_user_entry

This user-defined strategy is used to spot a trend reversal after a stock break out of its opening range.  First, opening range period is defined as the first 30 minutes of the trading day (6:30 through 7:00 am PST).  This would set the high and low of the opening price range.  The difference between the high and the low of the opening price range must first be compared to the Average True Range (ATR) of the stock.  The entry condition below should only be condidered if and only if the opening range is larger than a certain multiple of the ATR (default at 1.0 times the ATR, made setable with range from 0.8 to 1.6).

We will enter a Long trade position if:
- a hammer candle or a bullish engulfing candle is shown on the close of a 5 minute bar and its body is completely out side of the opening range.
- the trade volume on the bar has to be at least 1.5 times the average volume of the opening range.

We will enter a Short trade position if:
- an invert hammer candle or a bearish engulfing candle is shown on the close of a 5 minute bar and its body is completely outside of the opening range.
- trade volume on the bar has to be at least 1.5 times the average volume of the opening range

* we should allow this strategy to be combined with other indicators such as MACD or RSI for more assurance.

3.  support_user_exit