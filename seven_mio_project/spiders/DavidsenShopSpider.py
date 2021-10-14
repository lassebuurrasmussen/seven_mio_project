import urllib.parse

import scrapy
from scrapy.http import TextResponse

from seven_mio_project.CustomExceptions import OutdatedError, UnexpectedResultError


def get_href_of_element_from_group(response: TextResponse, element_name: str, element_group_css_query: str) -> str:
    """
    Raises:
        OutdatedError: When CSS query seems to have been outdated by update to website HTML.
        UnexpectedResultError: If elements of the group return multiple text strings when calling
            element_selector.css("::text").getall()
    """
    # TODO:
    #  This could potentially just take a list of categories and follow them all:
    #       ```
    #       yield from response.follow_all(css='ul.pager a', callback=self.parse)
    #       ```
    element_group_selector = response.css(element_group_css_query)

    # TODO:
    #  It is possible for a single `a` element to return mutltiple text strings. E.g.
    #  ```
    #  >>> response.css("div.sc-bxivhb.bHTkun div div ul li a")[0].css("::text").getall()
    #  [' ', 'Træ']
    #  ```
    #  So I somehow need to handle that. I can't just look at the first text string of the `a` element to determine
    #  which one to get href attribute from. Works fine for self.parse as it is, but not for parse_main_category_page.
    if not all([len(selector.css("::text").getall()) == 1 for selector in element_group_selector]):
        raise UnexpectedResultError(
            "At least one element contained multiple text parts. Please make a more specific CSS query"
        )

    # Note that .css("::text").getall() only returns `str` for those elements that have text. So len(Selectorlist) is
    # not neccesarily same as len(Selectorlist"::text").getall()). So we use .get() method instead
    element_name_to_element_selector_dict: dict[str, scrapy.Selector] = {
        selector.css("::text").get().lower(): selector for selector in element_group_selector
    }

    try:
        element_selector = element_name_to_element_selector_dict[element_name]
    except KeyError as error:
        raise OutdatedError(
            f'"{element_name}" is not key of selector dict. {element_name_to_element_selector_dict.keys()=}'
        ) from error

    return element_selector.attrib["href"]


class DavidsenshopSpider(scrapy.Spider):
    name = "DavidsenShopSpider"
    start_urls = ["https://www.davidsenshop.dk/"]

    def parse(self, response: TextResponse, **kwargs):
        try:
            byg_main_category_url = get_href_of_element_from_group(
                response=response,
                element_name="byg",
                element_group_css_query="div.QuickBasketAndMenus__MenuWrapper-sc-17cnu5q-20.fQBxeN div ul li a",
            )
        except OutdatedError:
            # Assume that byg page URL itself has not changed
            byg_main_category_url = "https://www.davidsenshop.dk/byg-c-id497143"

        yield response.follow(byg_main_category_url, callback=self.parse_main_category_page)

    def parse_main_category_page(self, response: TextResponse):
        # TODO: Remove this
        response.css("div.sc-bxivhb.bHTkun div div ul li a").getall()

        tree_sub_category_url = get_href_of_element_from_group(
            response=response, element_name="træ", element_group_css_query="div.sc-bxivhb.bHTkun div div ul li a"
        )
