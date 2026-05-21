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