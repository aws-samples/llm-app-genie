# Scrapy settings for webchat project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "crawly"

SPIDER_MODULES = ["crawly.spiders"]
NEWSPIDER_MODULE = "crawly.spiders"

RETRY = True
RETRY_TIMES = 10
RETRY_DELAY = 30
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429, 403]

# Crawl responsibly by identifying yourself (and your website) on the user-agent
# USER_AGENT = "webchat (+http://www.yourdomain.com)"

# Obey robots.txt rules
ROBOTSTXT_OBEY = True

# # file download settings
# ITEM_PIPELINES = {'scrapy.pipelines.files.FilesPipeline': 1}
# FILES_STORE = '.tmp_file_downloads'


# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

DOWNLOADER_MIDDLEWARES = {
    "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
    "custom_middlewares.CustomRetryMiddleware": 300,
    "scrapy_user_agents.middlewares.RandomUserAgentMiddleware": 400,
}
