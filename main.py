"""Script to run scrapy crawl directly in PyCharm.

Allows for debugging
"""
from scrapy import cmdline

cmdline.execute("scrapy crawl DavidsenShopSpider".split())
