import boto3
import json

import requests
from markdownify import markdownify

import os
import re
import time
from tqdm import tqdm
from datetime import datetime, timedelta
import finnhub
from alpaca_trade_api.rest import REST, TimeFrame
import pandas as pd
import defusedxml.ElementTree as ET
from modules.aws_helpers import get_credentials, read_from_s3, s3_client


# Setting up keys for finnhub and alpaca APIs
if os.environ["APIS_SECRET"] == "":
    print("No API keys provided, skipping data download")
    exit(0)

api_keys = get_credentials(os.environ["APIS_SECRET"])

finnhub_api_key = api_keys["finnhub_api_key"]
os.environ['APCA_API_KEY_ID'] = api_keys["apca_api_key_id"]
os.environ['APCA_API_SECRET_KEY'] = api_keys["apca_api_secret_key"]
os.environ['APCA_API_BASE_URL'] = 'https://paper-api.alpaca.markets'

# S3 bucket and prefix for market data
s3_bucket = os.environ["S3_BUCKET"]
s3_prefix = os.getenv("S3_PREFIX")
delimiter = "/"

finnhub_client = finnhub.Client(api_key=finnhub_api_key)
api = REST()

# Use dynamic dates for download
start_date = (datetime.now() - timedelta(days=364)).strftime('%Y-%m-%d')
end_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
debug_mode = False

print(f""" Getting the data betwenn {start_date} and  {end_date}. """)

s3 = boto3.client("s3")

data_sources=[
    {"ticker": "UBS"}, 
    {"ticker": "AMZN"}, 
    {"ticker": "GOOGL"}, 
    {"ticker": "AAPL"}
]

document_types=[
    "10-K",     # Annual report filed by public companies. Provides comprehensive summary of company's performance. Contains audited financial statements.
    "10-Q",     # Quarterly report filed by public companies. Provides unaudited financial statements and update on operations. 
    "11-K",      # Annual report filed by foreign companies.
    "6-K",      # REPORT OF FOREIGN PRIVATE ISSUER (UBS)
    # # Skipping 8-K for now, as it often references other documents without substantial standalone information
    # "8-K",    # Report on material events or corporate changes which is filed as needed. Used to announce major events like mergers, CEO change, bankruptcy.
    "DEF 14A",  # Definitive proxy statement which details information for shareholders ahead of annual shareholder meeting.
    "13F-HR",   # Required quarterly filing by institutional investment managers detailing their equity holdings. 
    # this is different file extension
    "4"         # Insider trading filing showing stock purchases/sales by corporate insiders.
]


# Company daily prices from 
def daily_prices(company):
    price_df = api.get_bars(company['ticker'], TimeFrame.Day, start_date, end_date, adjustment='raw').df
    price_df["ticker"] = company['ticker']
    
    file_path = f"s3://{s3_bucket}/{s3_prefix}/{company['ticker']}/daily_prices.csv"

    price_df.to_csv(file_path, index=True)

def parse_sec_filling(url, debug = False):
    # Check the instructions and limitations from 
    # https://www.sec.gov/about/webmaster-frequently-asked-questions#developers
    headers = {
        "User-Agent": api_keys["user_agent_email"],
        "Accept-Encoding": "gzip, deflate",
        "Host": "www.sec.gov"
    }

    # Fetch HTML content from the web URL
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error: {response.status_code}, {response.content}")
        return

    html_content = response.text

    if debug:
        file_name = "debug/" + url.split("/")[-1]
        
        # open file instead of downloading
        # with open(file_name, 'r ,encoding="utf8") as file:
        #     html_content = file.read()

        with open(file_name, 'w',encoding="utf8") as file:
            file.write(html_content)

    # cutting XML header
    start_from = 0
    if url.endswith(('htm', 'html')):
        md = markdownify(html_content)

        match = re.search(r'\**UNITED\s+STATES\**', md)
        start_from = match.start() if match else 0

        content = md[start_from:]
    else:
        md = parse_xml_content_to_text(html_content)
        content = md

    if debug:
        print(f"Parsing url: {url} cutting from: {start_from} ")
        with open(file_name + "-markdownify.md", 'w',encoding="utf8") as file:
            file.write(md)
        with open(file_name + "-markdownify-cleared.md", 'w',encoding="utf8") as file:
            file.write(content)

    return markdownify(content)

def parse_xml_content_to_text(xml_content):
    # Parse the XML content from the string
    root = ET.fromstring(xml_content)

    # Initialize an empty string to store the extracted text
    extracted_text = ""

    # Function to recursively extract text from XML elements
    def extract_text(element, indent=""):
        text = ""
        if element.text and element.text.strip():
            text += indent + element.tag + ": " + element.text.strip() + "\n"
        for child in element:
            text += extract_text(child, indent + "  ")
        return text

    # Extract text from the root element
    extracted_text = extract_text(root)
    
    return extracted_text
def company_sec_parser(sec_filing, path):
    # Filter elements with reportUrl ending in htm or html
    filtered_data = [element for element in sec_filing if element['reportUrl'].endswith(('htm', 'html')) and element["form"] in document_types]

    # Print the filtered data
    for element in tqdm(filtered_data):
        element["content"] = parse_sec_filling(element["reportUrl"], debug=debug_mode)
        element["size"] = len(element["content"])
        time.sleep(0.1)

    s3.put_object(Bucket=s3_bucket, Key=path + "sec_filings_content.json", Body=json.dumps(filtered_data))


def finance_information(company):
    file_path = f"{s3_prefix}/{company['ticker']}/"

    # getting company profile to extent the metadata
    profile =  finnhub_client.company_profile2(symbol=company['ticker'])
    for key, value in profile.items():
        if key in ['ticker']:
            continue
        company[key] = value
        
    # # Future use
    # # news are mainly headlines and don't have much sense    
    # news = finnhub_client.company_news(company['ticker'], _from=start_date, to=end_date)
    # s3.put_object(Bucket=s3_bucket, Key=file_path + "news.json", Body=json.dumps(news))
    
    # # basic financial (yearly and quarterly)    
    # basic_financials = finnhub_client.company_basic_financials(company['ticker'], 'all')
    # s3.put_object(Bucket=s3_bucket, Key=file_path + "basic_financials.json", Body=json.dumps(basic_financials))

    # # Insider Transactions
    # # detailes for codes: https://www.sec.gov/about/forms/form4data.pdf
    # insider_transactions = finnhub_client.stock_insider_transactions(company['ticker'])
    # s3.put_object(Bucket=s3_bucket, Key=file_path + "insider_transactions.json", Body=json.dumps(insider_transactions))

    # # Insider Sentiment
    # # Method is here: https://medium.com/@stock-api/finnhub-insiders-sentiment-analysis-cc43f9f64b3a
    # insider_sentiment = finnhub_client.stock_insider_sentiment(company['ticker'], _from=start_date, to=end_date)
    # s3.put_object(Bucket=s3_bucket, Key=file_path + "insider_sentiment.json", Body=json.dumps(insider_sentiment))

    # # Financials As Reported
    # financials_as_reported = finnhub_client.financials_reported(symbol = company['ticker'], freq='quarterly')
    # s3.put_object(Bucket=s3_bucket, Key=file_path + "financials_as_reported.json", Body=json.dumps(financials_as_reported))

    # SEC Filings        
    data = finnhub_client.filings(symbol = company['ticker'], _from=start_date, to=end_date)
    
    for item in data:
        for key, value in company.items():
            item[key] = value
    
    s3.put_object(Bucket=s3_bucket, Key=file_path + "sec_filings.json", Body=json.dumps(data))
    
    # Generating sec_filings_content.json by parsing the web reports
    company_sec_parser(data, file_path)


def prepare_embedding_docs():
    # get the list of available stock data
    response = s3_client.list_objects_v2(Bucket=s3_bucket, Prefix=s3_prefix + delimiter, Delimiter=delimiter)

    # Loading company prices and announcements from S3 into data frames
    prices_df = pd.DataFrame()
    announcement_df = pd.DataFrame()

    for content in response.get('CommonPrefixes', []):
        company = content.get('Prefix').replace(s3_prefix, "").replace(delimiter, "")

        prices_df = pd.concat([prices_df, read_from_s3(s3_bucket, f"""{s3_prefix}/{company}/daily_prices.csv""", "csv")], ignore_index=True)
        announcement_df = pd.concat([announcement_df, read_from_s3(s3_bucket, f"""{s3_prefix}/{company}/sec_filings_content.json""", "json")], ignore_index=True)

    # adjusting dataframes based on retriever needs
    prices_df['opening price'] = prices_df['open']
    prices_df['date'] = pd.to_datetime(prices_df['timestamp']).dt.date
    prices_df['change from previous day'] = (prices_df['open'].pct_change()*100).round(2).astype(str) + '%'

    announcement_df['id'] = announcement_df['symbol'] + "|" + announcement_df['acceptedDate'].str.split().str[0] + "|" + announcement_df['form']
    announcement_df['date'] = pd.to_datetime(announcement_df['acceptedDate']).dt.date
    announcement_df['date_full'] = pd.to_datetime(announcement_df["acceptedDate"]).dt.strftime("%B %d, %Y")
    announcement_df['title'] = announcement_df["symbol"] + " " + announcement_df["form"] + " announcement from "  + announcement_df["date_full"]
    announcement_df = announcement_df.sort_values('acceptedDate', ascending=False)

    # Defining embedding template
    template = """
    <{0} ({1}) {2} announcement from {3}>
    {4}
    </{0} ({1}) {2} announcement from {3}>
    """

    split_by = "\n---\n"

    docs = []
    max_character_limit = 14000 # Max input tokens: 8192

    for _, row in tqdm(announcement_df.iterrows()):
        metadata = {
            "stock": row["symbol"],
            "ticker": row["symbol"], 
            "source": row["reportUrl"], 
            "company name": row["name"],
            "date": row.date_full,
            "type": row["form"],
            "title": row.title,
            "cik": row["cik"]                
        }        

        # TODO: Chunck the documents if split doesn't work or it is too long
        for index, item in enumerate(row.content.split(split_by)):
            if len(item) > max_character_limit:
                print(f"Content for {row.title} is {len(item)}, which is too long, check the split \n\n {metadata}")
                continue
            metadata["part"] = index
            cont = template.format(
                row["name"],
                row["symbol"], 
                row["form"],
                row.date_full, 
                item
            )
            
            docs.append({"page_content": cont, "metadata": metadata.copy()})

    # upload docs as JSON file to s3_bucket
    if len(docs) > 0:
        s3.put_object(Bucket=s3_bucket, Key=f"{s3_prefix}/embedding_docs.json", Body=json.dumps(docs))

for company in tqdm(data_sources):
    daily_prices(company)
    finance_information(company)

prepare_embedding_docs()
