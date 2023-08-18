# Version 1.1.5

1. Adjusted the way of loading strategy initialization data in the backtesting engine (using the backtesting start date to be loaded by natural days)
2. Adjust the output method of optimization results (replace strings with dictionaries)
3. Remove the direct return logic when the transaction record is empty.

# Version 1.1.4

1. Filter TargetPosTemplate templates when loading strategy class
2. When removing a strategy configuration, delete the strategy's cached data at the same time

# Version 1.1.3

1. Use the unified timezone defined in vnpy.trader.database to load the data
2. Add contract multiplier query function get_size to policies
3. Change to use the OffsetConveter provided by the main engine, no longer independently maintained
4. Increase the log output during the process of calling the data service to obtain historical data
5. Add the max_workers parameter to control the number of optimization processes.

# Version 1.1.2

1. Add a check on the situation of funds burst (less than or equal to 0) during backtesting.

# 1.1.1 version

1. Use zoneinfo to replace pytz library
2. Adjust the installation script setup.cfg to add Python version restriction.

# 1.1.0 version

1. Add strategy instance lookup function
2. Remove reverse contract support
3. Fix the percentage retracement calculation problem in the backtest statistics

# 1.0.9 version

1. Improve variable and function type declarations
2. Sort strategy names in the strategy drop-down box by first letter.
3. Replace QtCore.pyqtSignal with PySide's QtCore.

# Signal to PySide's QtCore.

1. Move asynchronous playback for loading historical data from the engine to the strategy template
2. Change the icon file information of the module to the full path string
