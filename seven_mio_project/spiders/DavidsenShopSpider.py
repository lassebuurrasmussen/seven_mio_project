import re
from functools import partial

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
                element_text="byg",
                element_group_css_query="div.QuickBasketAndMenus__MenuWrapper-sc-17cnu5q-20.fQBxeN div ul li a",
            )
        except OutdatedError:
            # Assume that byg page URL itself has not changed
            byg_main_category_url = "https://www.davidsenshop.dk/byg-c-id497143"

        yield response.follow(byg_main_category_url, callback=self.parse_main_category_page)

    def parse_main_category_page(self, response: TextResponse):
        tree_sub_category_url = get_href_of_element_from_group(
            response=response, element_text="træ", element_group_css_query="div.sc-bxivhb.bHTkun div div ul li a"
        )
        yield response.follow(tree_sub_category_url, callback=self.parse_sub_category_pages)

    def parse_sub_category_pages(self, response: TextResponse):

        for sub_category in [
            "lægter",
            "reglar",
        ]:
            laegter_sub_category_url = get_href_of_element_from_group(
                response=response,
                element_text=sub_category,
                element_group_css_query="div.sc-bxivhb.bHTkun div div ul li a",
            )
            yield response.follow(
                laegter_sub_category_url, callback=partial(self.parse_item_list_page, sub_category=sub_category)
            )

    def parse_item_list_page(self, response: TextResponse, sub_category: str):
        item_selectors = response.css("div.sc-bxivhb.kRNIyz > ul > li")

        for item_index, item_selector in enumerate(item_selectors):
            item_data = {"sub_category": sub_category}
            item_selector: Selector

            full_name = item_selector.css("div > div:nth-child(1) > a > div:nth-child(2)::text").get()
            name, dimensions, dimensions_unit = extract_dimensions_from_full_name(full_name)
            item_data.update(
                {"full_name": full_name, "name": name, "dimensions": dimensions, "dimensions_unit": dimensions_unit}
            )

            price_per_unit = item_selector.css("div > div:nth-child(2) > div:nth-child(1) > div > span::text").get()
            price_per_item = item_selector.css(
                "div > div > div:nth-child(1) > div.styles__DiscountWrap-sc-2i08oq-7::text"
            ).getall()[1]
            item_data["price_per_unit"] = format_price_with_comma(price_per_unit)
            item_data["price_per_item"] = format_price_with_comma(price_per_item)

            unit = item_selector.css("div > div > div:nth-child(1) > div:nth-child(1) > div::text").get()
            item_data["unit"] = unit.strip("kr./")

            item_data["url"] = item_selector.css("div > div:nth-child(1) > a").attrib["href"]

            yield item_data


def get_href_of_element_from_group(response: TextResponse, element_text: str, element_group_css_query: str) -> str:
    """
    Raises:
        OutdatedError: When CSS query seems to have been outdated by update to website HTML.
        UnexpectedResultError: If multiple elements of the group return text strings that equal element_text.
    """
    # TODO:
    #  This could potentially just take a list of categories and follow them all:
    #       ```
    #       yield from response.follow_all(css='ul.pager a', callback=self.parse)
    #       ```
    element_group_selector = response.css(element_group_css_query)
    element_group_texts_dict = extract_all_element_group_texts(element_group_selector)
    element_index = get_dict_key_with_value_containing_target(
        dictionary=element_group_texts_dict, target_string=element_text
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


def extract_dimensions_from_full_name(full_name: str) -> tuple[str, str, str]:
    dimension_pattern = r" (\d+ ?x ?\d+) (\w+)"
    dimension_match = re.search(dimension_pattern, full_name)

    dimensions, dimensions_unit = dimension_match.groups()
    dimensions = dimensions.replace(" ", "")

    name = full_name[: dimension_match.start()]

    return name, dimensions, dimensions_unit


def format_price_with_comma(price: str) -> float:
    comma_count = price.count(",")
    assert comma_count == 1, f'price contained more or less than one ",". {price=}'
    assert "." not in price, f'price already contained ".". {price=}'
    return float(price.replace(",", "."))
