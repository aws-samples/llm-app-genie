""" Module that contains tools for agents. """

from pandas_datareader import data as pdr
import yfinance as yf
from bs4 import BeautifulSoup
import re
import requests
from datetime import date
from datetime import timedelta
def get_stock_price(ticker, history=60):
    yf.pdr_override()
    today = date.today()
    start_date = today - timedelta(days=history)
    data = pdr.get_data_yahoo(ticker, start=start_date, end=today)
    dataname = ticker + '_' + str(today)
    return data, dataname

# Fetch top 5 google news for given company name
def google_query(search_term):
    if "news" not in search_term:
        search_term = search_term + " stock news"
    url = f"https://www.google.com/search?q={search_term}"
    url = re.sub(r"\s", "+", url)
    return url

def get_recent_stock_news(company_name):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'}

    g_query = google_query(company_name)
    res = requests.get(g_query, headers=headers, timeout=0.5)
    res.raise_for_status()
    
    soup = BeautifulSoup(res.text, "html.parser")
    news = []
    for n in soup.find_all("div", "n0jPhd ynAwRc tNxQIb nDgy9d"):
        news.append(n.text)
    for n in soup.find_all("div", "IJl0Z"):
        news.append(n.text)

    if len(news) > 6:
        news = news[:4]
    else:
        news = news
    news_string = ""
    for i, n in enumerate(news):
        news_string += f"{i}. {n}\n"
    top5_news = "Recent News:\n\n" + news_string

    return top5_news

# Get financial statements from Yahoo Finance
def get_financial_statements(ticker):
    if "." in ticker:
        ticker = ticker.split(".")[0]
    else:
        ticker = ticker
    company = yf.Ticker(ticker)
    balance_sheet = company.balance_sheet
    if balance_sheet.shape[1] >= 3:
        balance_sheet = balance_sheet.iloc[:, :3]  # Only captures last 3 years of data
    balance_sheet = balance_sheet.dropna(how="any")
    balance_sheet = balance_sheet.to_string()
    return balance_sheet
