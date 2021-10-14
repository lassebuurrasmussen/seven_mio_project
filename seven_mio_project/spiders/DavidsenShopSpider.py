import urllib.parse

import scrapy
from scrapy.http import TextResponse

from seven_mio_project.CustomExceptions import OutdatedError


def get_byg_url(response: TextResponse) -> str:
    """
    Raises:
        OutdatedError: When CSS query seems to have been outdated by update to website HTML.
    """
    main_categories_css = "div.QuickBasketAndMenus__MenuWrapper-sc-17cnu5q-20.fQBxeN div ul li a"

    main_categories_selector = response.css(main_categories_css)
    main_category_texts: list[str] = [selector.css("::text").get().lower() for selector in main_categories_selector]

    try:
        byg_index = main_category_texts.index("byg")
    except ValueError as e:
        raise OutdatedError(f'"byg" is not part of main_category_texts list. {main_category_texts=}') from e

    byg_sub_url = main_categories_selector[byg_index].css("::attr(href)").get()
    byg_url = urllib.parse.urljoin(response.url, byg_sub_url)

    return byg_url


class DavidsenshopSpider(scrapy.Spider):
    # TODO: Got to:
    #  https://docs.scrapy.org/en/latest/intro/tutorial.html#extracting-data-in-our-spider
    name = "DavidsenShopSpider"
    start_urls = ["https://www.davidsenshop.dk/"]

    def parse(self, response: TextResponse, **kwargs):
        try:
            byg_url = get_byg_url(response)
        except OutdatedError:
            # Assume that byg page URL itself has not changed
            byg_url = "https://www.davidsenshop.dk/byg-c-id497143"

        yield {
            "url": byg_url,
            "name": "byg_url",
        }
