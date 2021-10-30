from pathlib import Path

import pandas as pd

import run_spider

excel_output_path = Path("spider_output/davidsen_shop.xlsx")

if __name__ == '__main__':
    pd.read_csv(run_spider.spider_output_path).to_excel(excel_output_path, index=False)
