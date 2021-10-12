import urllib.parse

import scrapy
from scrapy.http import TextResponse


def get_byg_url(response: TextResponse) -> str:
    css_main_categories = "div.QuickBasketAndMenus__MenuWrapper-sc-17cnu5q-20.fQBxeN div ul li a"
    text_extraction_css_suffix = "::text"

    main_categories: list[str] = response.css(css_main_categories + text_extraction_css_suffix).getall()
    main_categories = [category.lower() for category in main_categories]

    byg_index = main_categories.index("byg")

    href_extraction_css_suffix = "::attr(href)"
    byg_sub_url = response.css(css_main_categories + href_extraction_css_suffix)[byg_index].get()
    byg_url = urllib.parse.urljoin(response.url, byg_sub_url)

    return byg_url


class DavidsenshopSpider(scrapy.Spider):
    # TODO: Got to:
    #  https://docs.scrapy.org/en/latest/intro/tutorial.html#extracting-data-in-our-spider
    name = "DavidsenShopSpider"
    start_urls = ["https://www.davidsenshop.dk/"]

    def parse(self, response: TextResponse, **kwargs):
        byg_url = get_byg_url(response)

        yield {
            "url": byg_url,
            "name": "byg_url",
        }
