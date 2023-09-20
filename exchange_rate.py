import yfinance as yf

currency_pair = yf.Ticker("CNYRUB=X")

data = currency_pair.history(period="1d")

last_price = round(data["Close"].iloc[-1], 1)
