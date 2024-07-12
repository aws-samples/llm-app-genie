""" Module that contains a class that represents a FinAnalyzer retriever catalog item. """
import os
from dataclasses import dataclass
from typing import Any, List, Tuple, Union
from langchain.schema import BaseRetriever

from ..catalog.retriever_catalog_item import RetrieverCatalogItem
from chatbot.fin_analyzer import FinAnalyzerIndexRetriever
import streamlit as st

import pandas as pd

import boto3
from io import StringIO

s3_client = boto3.client('s3')

@dataclass
class FinAnalyzerRetrieverItem(RetrieverCatalogItem):
    """Class that represents a FinAnalyzer retriever catalog item."""

    # config: FinAnalyzerParameters
    # """Finance Analyzer configuration"""

    region: str
    """ AWS Region """
    index_id: str
    """ FinAnalyzer Index ID """

    _data_sources: Any
    """ FinAnalyzer Data Sources in this index """

    _selected_data_sources: List[Tuple[str, Any]]

    """ FinAnalyzer Data Source IDs that the retriever is supposed to use at the moment. """

    def __init__(self, index_id, config, region=None):
        super().__init__(config["friendlyName"])
        self._selected_data_sources = []
        self.index_id = index_id
        self.region = region

        # get the list of available stock data
        response = s3_client.list_objects_v2(Bucket=os.environ["DATA_SOURCES_S3_BUCKET"], Prefix=os.environ["FIN_ANALYZER_S3_PREFIX"] + "/", Delimiter="/")
        
        # Loading company prices and announcements from S3 into data frames
        self._data_sources = []
        self.prices_df = pd.DataFrame(columns=['open', 'timestamp'])
        self.announcement_df = pd.DataFrame(columns=['symbol', 'acceptedDate', 'form', 'date_full', 'title', 'date'])

        companies_data_folders = response.get('CommonPrefixes', [])
        
        for content in companies_data_folders:
            company = content.get('Prefix').replace(os.environ["FIN_ANALYZER_S3_PREFIX"], "").replace("/", "")
            
            self.prices_df = pd.concat([self.prices_df, self.read_from_s3(os.environ["DATA_SOURCES_S3_BUCKET"], f"""{os.environ["FIN_ANALYZER_S3_PREFIX"]}/{company}/daily_prices.csv""", "csv")], ignore_index=True)
            self.announcement_df = pd.concat([self.announcement_df, self.read_from_s3(os.environ["DATA_SOURCES_S3_BUCKET"], f"""{os.environ["FIN_ANALYZER_S3_PREFIX"]}/{company}/sec_filings_content.json""", "json")], ignore_index=True)

            self._data_sources.append({
                "stock": company
            })
        
        
        # adjusting dataframes based on retriever needs
        self.prices_df['opening price'] = self.prices_df['open']
        self.prices_df['date'] = pd.to_datetime(self.prices_df['timestamp']).dt.date
        self.prices_df['change from previous day'] = (self.prices_df['open'].pct_change()*100).round(2).astype(str) + '%'

        self.announcement_df['id'] = self.announcement_df['symbol'] + "|" + self.announcement_df['acceptedDate'].str.split().str[0] + "|" + self.announcement_df['form']
        self.announcement_df['date'] = pd.to_datetime(self.announcement_df['acceptedDate']).dt.date
        self.announcement_df['date_full'] = pd.to_datetime(self.announcement_df["acceptedDate"]).dt.strftime("%B %d, %Y")
        self.announcement_df['title'] = self.announcement_df["symbol"] + " " + self.announcement_df["form"] + " announcement from "  + self.announcement_df["date_full"]
        self.announcement_df = self.announcement_df.sort_values('acceptedDate', ascending=False)

    @property
    def available_filter_options(self) -> Union[List[Tuple[str, Any]], None]:
        return [(data_src["stock"], data_src) for data_src in self._data_sources]

    @property
    def current_filter(self) -> List[str]:
        return [
            (data_src["stock"], data_src) for data_src in self._selected_data_sources
        ]

    @current_filter.setter
    def current_filter(self, value: List[Tuple[str, Any]]):
        selected_and_part_of_index = list(
            filter(lambda x: x[1] in self._data_sources, value)
        )
        self._selected_data_sources = selected_and_part_of_index

    def get_instance(self) -> BaseRetriever:
        if not hasattr(self, 'announcement_filter') or len(self.announcement_filter) == 0:
            st.error('Please select one or more company announcements.')
            return
        
        retriever = FinAnalyzerIndexRetriever(self.announcement_df, self.prices_df, self.announcement_filter)
        return retriever
    
    def read_from_s3(self, bucket, key, format):
        obj = s3_client.get_object(Bucket=bucket, Key=key)
        data = obj['Body'].read().decode('utf-8')
        print(data)
        
        if format == "csv":
            return pd.read_csv(StringIO(data))
        elif format == "json":
            return pd.read_json(StringIO(data))