"""Chain for question-answering against a vector database."""
from __future__ import annotations

import logging
import pandas as pd
from typing import Any, List, Tuple, Union
from tabulate import tabulate

# Streamlit plot integration
from plotnine import *

from chatbot.helpers.logger import TECHNICAL_LOGGER_NAME
from langchain.schema import BaseRetriever, Document

import boto3
from io import StringIO

logger = logging.getLogger(TECHNICAL_LOGGER_NAME)
s3_client = boto3.client('s3')

class FinAnalyzerIndexRetriever(BaseRetriever):
    """Retriever to search Financial Documentation.

    Args:
        announcement_df: Announcements dataframe.
        prices_df: Daily prices dataframe.
        announcement_filter: User selected filter on GUI.
        max_character_limit: Maximum character limit for each document. Default: 80000

    Example:
        ```python
        retriever = FinAnalyzerIndexRetriever(self.announcement_df, self.prices_df, self.announcement_filter)
        ```
    """

    prices_df = pd.DataFrame()
    announcement_df = pd.DataFrame()

    plot_requested = False
    graphs = {}
    max_character_limit: int

    def __init__(
        self,
        announcement_df,
        prices_df,
        announcement_filter: List,
        # TODO: Move to the appconfig together with max number of documents to select
        max_character_limit: int = 80000
    ):        
        super().__init__(
            max_character_limit=max_character_limit,
            announcement_df=announcement_df[announcement_df.id.isin(announcement_filter)],
            prices_df=prices_df
        )

    def read_from_s3(self, bucket, key):
        obj = s3_client.get_object(Bucket=bucket, Key=key)
        data = obj['Body'].read().decode('utf-8')
        return pd.read_csv(StringIO(data))
    
    def get_price_changes(self, price_condition, open_end, company):
        price_query = "date {0} @open_end and ticker == @company"
        price_change = self.prices_df.query(price_query.format(price_condition))

        # Formatting price change for output
        formatted_change = price_change[["ticker", "date", "opening price", "change from previous day"]]
        if price_condition == '<=':
            formatted_change = formatted_change.iloc[-5:]
        elif price_condition == '>=':
            formatted_change = formatted_change.iloc[1:6]
        else:
            return "Wrong condition."
        
        return formatted_change
    
    def get_relevant_documents(self, query: str) -> List[Document]:
        """Run search on FinAnalyzer data source and get top k documents.

        Args:
            query: Query string.

        Returns:
            list of documents from this OpenSearch index that relate to the query.
        """

        template = """
<{0} ({1}) {2} announcement from {3}>
{4}
</{0} ({1}) {2} announcement from {3}>
        """

        # initialize list for documents and plots
        docs = []
        plot_data = {}

        for _, row in self.announcement_df.iterrows():
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
            
            open_change_before = self.get_price_changes("<=", row.date, row["symbol"])
            open_change_after = self.get_price_changes(">=", row.date, row["symbol"])

            cont = template.format(
                row["name"],
                row["symbol"], 
                row["form"],
                row.date_full, 
                row.content[:int(min(self.max_character_limit, len(row.content)))], 
                # tabulate(open_change_before, headers='keys', tablefmt='pipe', showindex=False),
                # tabulate(open_change_after, headers='keys', tablefmt='pipe', showindex=False)
            )

            docs.append(Document(page_content = cont, metadata = metadata))

            if self.plot_requested:
                plot_open_change_before = pd.DataFrame({
                    'Date' : pd.to_datetime(open_change_before['date']).dt.normalize(),
                    'Price' : open_change_before["opening price"]
                })
                plot_open_change_after = pd.DataFrame({
                    'Date' : pd.to_datetime(open_change_after['date']).dt.normalize(),
                    'Price' : open_change_after["opening price"]
                })
                if row["name"] not in plot_data:
                    plot_data[row["name"]] = pd.DataFrame(columns=['Date', 'Price'])

                plot_data[row["name"]] = pd.concat([plot_data[row["name"]], plot_open_change_before, plot_open_change_after], ignore_index = True)

        # MM:: Convert to picture and Dataframe instead of plot object
        if self.plot_requested:
            # We can use standard Streamline graphs, but this allows standard plot integration
            # https://stackoverflow.com/questions/52463431/how-to-change-display-format-of-time-in-seconds-to-date-in-x-axis-in-bokeh-chart
            # https://docs.streamlit.io/library/api-reference/charts/st.bokeh_chart
            
            for title, plot in plot_data.items():
                p = ggplot(plot, aes('Date','Price')) + \
                    geom_line(color='blue') + \
                    scale_y_continuous(limits=[min(plot['Price']), max(plot['Price'])]) + \
                    ggtitle(title + " price history") + xlab('Date') + ylab('Price')

                # adding the announcement price
                for _, row in self.announcement_df[self.announcement_df.name.isin([title])].iterrows():
                    p = p + geom_vline(xintercept = row.date, color="green", linetype="dashed")
                
                self.graphs[title] = p

        return docs

    async def aget_relevant_documents(self, query: str) -> List[Document]:
        """See base class."""
        return await super().aget_relevant_documents(query)
