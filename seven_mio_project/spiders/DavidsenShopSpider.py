import scrapy
from scrapy import Selector
from scrapy.http import TextResponse
from scrapy.selector import SelectorList

from seven_mio_project.CustomExceptions import OutdatedError, UnexpectedResultError


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
        tree_sub_category_url = get_href_of_element_from_group(
            response=response, element_name="træ", element_group_css_query="div.sc-bxivhb.bHTkun div div ul li a"
        )

        # TODO: Follow tree_sub_category_url to get to lægter, so we can start scraping "Lægter" and "Reglar"
        yield {"tree_sub_category_url": tree_sub_category_url}


def get_href_of_element_from_group(response: TextResponse, element_name: str, element_group_css_query: str) -> str:
    """
    Raises:
        OutdatedError: When CSS query seems to have been outdated by update to website HTML.
        UnexpectedResultError: If multiple elements of the group return text strings that equal element_name.
    """
    # TODO:
    #  This could potentially just take a list of categories and follow them all:
    #       ```
    #       yield from response.follow_all(css='ul.pager a', callback=self.parse)
    #       ```
    element_group_selector = response.css(element_group_css_query)
    element_group_texts_dict = extract_all_element_group_texts(element_group_selector)
    element_index = get_dict_key_with_value_containing_target(
        dictionary=element_group_texts_dict, target_string=element_name
    )

    return element_group_selector[element_index].attrib["href"]


def get_dict_key_with_value_containing_target(dictionary: dict[int, list[str]], target_string: str) -> int:
    element_index = [i for i, element_texts in dictionary.items() if target_string in element_texts]

    n_element_hits = len(element_index)
    if n_element_hits > 1:
        raise UnexpectedResultError(f'Multiple elements had a text string equal to "{target_string}"')
    elif n_element_hits < 1:
        raise OutdatedError(f'"{target_string}" is not in element_group_texts_dict. {dictionary.values()=}')
    return element_index[0]


def extract_all_element_group_texts(element_group_selector: SelectorList) -> dict[int, list[str]]:
    return {
        i: extract_all_lower_case_texts(selector=element_selector)
        for i, element_selector in enumerate(element_group_selector)
    }


def extract_all_lower_case_texts(selector: Selector) -> list[str]:
    return [element_text.lower() for element_text in selector.css("::text").getall()]
