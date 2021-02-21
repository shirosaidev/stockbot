# stockbot Change Log

## [0.1-b.3] = 2021-02-21
### added
- new settings to config.py.sample, copy to your config and edit as needed
- added "lowtohigh" to cli -t tradealgo options
- you can now set your days and times for getting stocks, buying/selling stocks, etc in config
- new settings in config for number of days to get stock prices for determing movement
- new settings in config for getting stock movement, either start/end price over last n days or averaging daily change over n days

## [0.1-b.2] = 2021-02-17
### fixed
- issue with connecting to nasdaq api url, nasdaq recently changed api url for stock screener
### added
- nasdaq api url to config.py.sample, copy to your config
### changed
- removed rating algo, nasdaq api removed metrics for determining "rating"

## [0.1-b.1] = 2021-02-10
### added
- first release