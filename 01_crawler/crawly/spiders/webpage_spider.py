import json
import os
import re
import sys

import scrapy

# from urllib.parse import urlparse
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import Spider
from scrapy_playwright.page import PageMethod


def set_playwright_true(request, response):
    request.meta["playwright"] = True
    return request


class WebpageSpider(Spider):
    # crawler name
    name = "webpage"
    meta_main = None
    link_extractor = LinkExtractor()

    # get the config file name parameter
    config_filename_parameter = sys.argv[-1].split("=")
    if config_filename_parameter[0] == "filename":
        config_filename = config_filename_parameter[1]
    else:
        raise AttributeError(
            "Crawling could not start: 'filename' parameter not found."
        )

    with open(config_filename, "r", encoding="utf8") as file:
        config = json.loads(file.read())

    max_depth = config["CRAWLER_DEPTH"]
    start_urls = config["start_urls"]
    custom_settings = config["custom_settings"]
    file_extensions = config["file_extensions"]

    # whitelist and blacklist rexexp patterns
    whitelist_patterns = config["whitelist_patterns"]
    blacklist_patterns = config["blacklist_patterns"]

    my_state = {}
    requested_urls = {}

    # check the URLs for proper domain and white and black lists
    def check_if_prefix_root(self, url):
        # target_parsed = urlparse(url)
        # root_path_suffix = "/".join(self.root_parsed.path.split("/")[:-1])

        # checking the blacklist, check blacklist
        for pattern in self.blacklist_patterns:
            if re.search(re.escape(pattern), url) is not None:
                return False

        for pattern in self.whitelist_patterns:
            if re.search(re.escape(pattern), url) is None:
                return False

        return True

        # # currently only domain checked and not subdomain
        # this could be done with whitelisting
        # if target_parsed.hostname.startswith(self.root_parsed.hostname) and target_parsed.path.startswith(root_path_suffix):
        #     return True

        # second criteria is not clear
        # return target_parsed.hostname.startswith(self.root_parsed.hostname) and target_parsed.path.startswith(root_path_suffix)

    def __init__(self, **kwargs):
        super(WebpageSpider, self).__init__(**kwargs)

        self.meta_main = dict(
            playwright=True,
            playwright_include_page=True,
            playwright_page_methods=[
                # PageMethod("wait_for_selector", "div.quote"),
                PageMethod(
                    "evaluate", "window.scrollBy(0, document.body.scrollHeight)"
                ),
                # PageMethod("wait_for_selector", "div.quote:nth-child(11)"),  # 10 per page
            ],
            playwright_context_kwargs={
                "bypass_csp": True,
            },
            source=None,
            errback=self.errback,
            link_text="",
        )

    def get_meta_with_source(self, source, source_meta=None):
        meta = self.meta_main.copy()
        meta["source"] = source
        if source_meta is None:
            meta["depth"] = 1
            meta["link_text"] = "root"
        else:
            meta["depth"] = source_meta["depth"] + 1
        return meta

    def start_requests(self):
        if not self.start_urls and hasattr(self, "start_url"):
            raise AttributeError(
                "Crawling could not start: 'start_urls' not found "
                "or empty (but found 'start_url' attribute instead, "
                "did you miss an 's'?)"
            )
        for url in self.start_urls:
            yield scrapy.Request(url, meta=self.get_meta_with_source("root"))

    def parse_additional_page(self, response, item):
        item["additional_data"] = response.xpath(
            '//p[@id="additional_data"]/text()'
        ).get()
        return item

    def parse_file(self, response):
        yield {"file_urls": [response.url]}

    async def parse(self, response):
        print(response.url)

        # set meta for root
        page = response.meta["playwright_page"]
        source_url = response.url

        self.my_state[source_url] = self.my_state.get(source_url, 0) + 1
        if self.my_state.get(source_url, 0) > 1:
            await page.close()
            return

        if response.meta["source"] == "root":
            # click cookies accept
            try:
                await page.get_by_role("button", name="Accept All Cookies").click()
            except:
                pass

        targets_all = []

        for link in self.link_extractor.extract_links(response):
            link_text = link.text.strip()

            _, extension = os.path.splitext(link.url)
            content_type = response.headers.get("Content-Type")

            if (
                self.check_if_prefix_root(link.url)
                and response.meta["depth"] <= self.max_depth
                and extension not in self.file_extensions
                and b"application/pdf" not in content_type
            ):
                self.requested_urls[link.url] = self.requested_urls.get(link.url, 0) + 1

                print(
                    f"Adding Text: {link_text}, Adding Source: {source_url}, Target: "
                    + str(link.url)
                )

                m = self.get_meta_with_source(source_url, response.meta)
                m["link_text"] = link.text
                link_request = scrapy.Request(link.url, callback=self.parse, meta=m)

                # depth check for the main page is enough
                # depth = m["depth"]
                # skip the page if it has been seen already
                # if depth>self.max_depth or self.my_state.get(link.url, 0): #or self.links_requested.get(link.url, 0) > 1:
                if self.my_state.get(link.url, 0):
                    # print(f"Skipping Text: Depth {depth}, {link_text}, Adding Source: {source_url}, Target: " + str(link.url))
                    pass
                else:
                    row = {
                        "level": response.meta["depth"],
                        "text": link_text,
                        "target_url": link.url,
                        "source_url": source_url,
                    }
                    # print(row)
                    targets_all.append(row)
                    yield link_request
            else:
                print(
                    f"Skipping Text: {link_text}, Adding Source: {source_url}, Target: "
                    + str(link.url)
                )

            targets_all.append({"text": link_text, "url": link.url})

        # we can make page screenshots if required
        # screenshot = await page.screenshot(path="example.png", full_page=True)

        content = await page.evaluate(
            """async () => {
  const readability = await import('https://cdn.skypack.dev/@mozilla/readability');
  return (new readability.Readability(document)).parse();
}"""
        )
        content["source"] = source_url
        content["target_urls"] = targets_all
        content["link_text"] = response.meta["link_text"]
        print(f"Outlinks: {len(targets_all)} Processed Page {source_url}")
        await page.close()

        # we can skip some pages here if required
        yield content

    async def errback(self, failure):
        page = failure.request.meta["playwright_page"]
        await page.close()
