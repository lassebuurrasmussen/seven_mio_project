"""Script to run scrapy crawl directly in PyCharm.

Allows for debugging
"""
from pathlib import Path

from scrapy import cmdline

spider_output_path = Path("spider_output/davidsen_shop.csv")

if __name__ == "__main__":
    cmdline.execute(f"scrapy crawl DavidsenShopSpider -O {spider_output_path}".split())
