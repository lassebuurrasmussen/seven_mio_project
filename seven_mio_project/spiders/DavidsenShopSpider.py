import re
from typing import Optional

import scrapy
from scrapy import Selector
from scrapy.http import TextResponse
from scrapy.selector import SelectorList

from seven_mio_project.CustomExceptions import OutdatedError, UnexpectedResultError


class DavidsenshopSpider(scrapy.Spider):
    name = "DavidsenShopSpider"
    start_urls = ["https://www.davidsenshop.dk/"]

    def parse(self, response: TextResponse, **kwargs):
        byg_main_category_url = get_href_of_element_from_group(
            response=response,
            element_text="byg",
            element_group_css_query="div.QuickBasketAndMenus__MenuWrapper-sc-17cnu5q-20.fQBxeN div ul li a",
        )

        yield response.follow(byg_main_category_url, callback=self.parse_main_category_page)

    def parse_main_category_page(self, response: TextResponse):
        tree_sub_category_url = get_href_of_element_from_group(
            response=response, element_text="træ", element_group_css_query="div.sc-bxivhb.bHTkun div div ul li a"
        )
        yield response.follow(tree_sub_category_url, callback=self.parse_sub_category_pages)

    def parse_sub_category_pages(self, response: TextResponse):
        sub_category_urls = get_sub_category_urls(response=response)

        for _sub_category, sub_category_url in sub_category_urls.items():
            yield response.follow(sub_category_url, callback=parse_item_list_page)


def parse_item_list_page(response: TextResponse):
    sub_category = response.css("div.sc-bwzfXH.Banner__Wrapper-sb1bas-0.ioOTOM > div > div > div > h1::text").get()
    item_selectors = response.css("div.sc-bxivhb.kRNIyz > ul > li")
    for item_index, item_selector in enumerate(item_selectors):
        item_data = {"sub_category": sub_category}
        item_selector: Selector

        full_name = item_selector.css("div > div:nth-child(1) > a > div:nth-child(2)::text").get()
        # TODO:
        #  - Sometimes dimensions have different units...
        #  https://www.davidsenshop.dk/nordic-deck-classic-greymix-22-x-140-mm-x-36-m-c-id509325-p-41501953674
        #  "22 x 140 mm x 3,6 m"
        name, dimensions, dimensions_unit = extract_dimensions_from_full_name(full_name)
        price_per_unit = get_price(
            item_selector=item_selector, css_query="div > div:nth-child(2) > div:nth-child(1) > div > span::text"
        )
        price_per_item = get_price(
            item_selector=item_selector,
            css_query="div > div > div:nth-child(1) > div.styles__DiscountWrap-sc-2i08oq-7::text",
        )
        item_data.update(
            {
                "full_name": full_name,
                "name": name,
                "dimensions": dimensions,
                "dimensions_unit": dimensions_unit,
                "price_per_item": price_per_item,
                "price_per_unit": price_per_unit,
            }
        )

        unit: str = item_selector.css("div > div > div:nth-child(1) > div:nth-child(1) > div::text").get()
        item_data["unit"] = unit.replace("kr./", "").rstrip(".")

        item_data["url"] = response.urljoin(item_selector.css("div > div:nth-child(1) > a").attrib["href"])

        yield item_data


def get_price(item_selector: Selector, css_query: str) -> Optional[float]:
    price_candidates = item_selector.css(css_query).getall()

    prices_with_float_format = [
        price_as_float
        for price_candidate in price_candidates
        if (price_as_float := try_to_convert_to_float(price_candidate)) is not None
    ]

    return prices_with_float_format[0] if len(prices_with_float_format) else None


def try_to_convert_to_float(inpt: str) -> Optional[float]:
    replacer_map = str.maketrans({".": "_", ",": "."})
    output = inpt.translate(replacer_map)
    try:
        return float(output)
    except ValueError:
        return None


def get_sub_category_urls(response: TextResponse) -> dict[str, str]:
    sub_categories_css_query = (
        "div.sc-bwzfXH.iQBFKU > div.sc-htpNat.japWOx > div.sc-bxivhb.bHTkun > div > div:nth-child(1) > ul > li"
    )

    sub_category_selectors = response.css(sub_categories_css_query)

    def get_sub_category_name(sub_category_selector: Selector) -> str:
        """Each `a` tag has two text elements. Extract the second one."""
        sub_category_name = sub_category_selector.css("a::text").getall()[1]
        return sub_category_name

    def does_element_contain_sub_category(sub_category_selector: Selector) -> bool:
        """
        Some of the `li` tags contain a "back" button or the main category.
        The ones that contain sub categories are recognized like this.
        """
        return sub_category_selector.attrib["class"].startswith("Filter__Item-sc")

    return {
        get_sub_category_name(sub_category_selector): sub_category_selector.css("a").attrib["href"]
        for sub_category_selector in sub_category_selectors
        if does_element_contain_sub_category(sub_category_selector)
    }


def replace_danish_letters(word: str) -> str:
    danish_letter_replacement_map_lower = {"æ": "ae", "ø": "oe", "å": "aa"}
    danish_letter_replacement_map_upper = {k.upper(): v.upper() for k, v in danish_letter_replacement_map_lower.items()}
    danish_letter_replacement_map = danish_letter_replacement_map_lower | danish_letter_replacement_map_upper

    danish_letter_replacement_map_unicode = str.maketrans(danish_letter_replacement_map)
    return word.translate(danish_letter_replacement_map_unicode)


def get_href_of_element_from_group(response: TextResponse, element_text: str, element_group_css_query: str) -> str:
    """
    Raises:
        OutdatedError: When CSS query seems to have been outdated by update to website HTML.
        UnexpectedResultError: If multiple elements of the group return text strings that equal element_text.
    """
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


def extract_dimensions_from_full_name(full_name: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    dimension_pattern = r" ([\d,]+) ?x ?([\d,]+) ?x? ?([\d,]*) (\w+)"
    dimension_match = re.search(dimension_pattern, full_name)

    if not dimension_match:
        return None, None, None

    d1, d2, d3, dimensions_unit = dimension_match.groups()
    dimension_values = [d1, d2, d3] if d3 else [d1, d2]
    dimensions_string = "x".join(dimension_values)

    name = full_name[: dimension_match.start()] + full_name[dimension_match.end():]

    return name, dimensions_string, dimensions_unit
