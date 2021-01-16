import csv
import itertools
import json
import multiprocessing
import os
import re
import shutil
import sys
import urllib.parse

import pandas
import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36"
}


def _make_request(_url: str, _index, _destination):
    response = requests.request("GET", _url, headers=headers)
    soup = BeautifulSoup(response.text.encode("utf8"), "html.parser")
    for tag_idx, tag in enumerate(
        soup.findAll("script", text=re.compile("searchData"))
    ):
        try:
            json_data = json.loads(tag.string.split(" = ")[1])
        except IndexError:
            continue
        file_name = os.path.join(
            _destination + f"searchMetaData_{_index}_{tag_idx}.json"
        )
        with open(file_name, "w") as json_file:
            json.dump(json_data, json_file)
        print(f"<-- saved temporary searchMetaData: {file_name}", flush=True)


def _download_images(_image_url, _file_name):
    response = requests.get(_image_url, stream=True, headers=headers)
    with open(_file_name, "wb") as out_file:
        shutil.copyfileobj(response.raw, out_file)
    print(f"<-- saved image: {_file_name}", flush=True)
    del response


def fetch_metadata(combinations, destination="./data/"):
    if not os.path.exists(destination):
        os.makedirs(destination)

    mp_pool = multiprocessing.Pool(multiprocessing.cpu_count())

    for index, comb in enumerate(list(itertools.product(*combinations))):
        url = f"https://www.myntra.com/{comb[0]}?f={urllib.parse.quote(comb[1])}&sort={comb[2]}&p={comb[3]}"
        print(f"--> fetching metadata from: {url}")
        mp_pool.apply_async(func=_make_request, args=(url, index, destination))
    mp_pool.close()
    mp_pool.join()

    json_files = [files for files in os.listdir(destination) if files.endswith(".json")]
    file_name = os.path.join(destination, "productData.csv")

    with open(file_name, mode="w", newline="") as product_catalog:
        writer = csv.writer(product_catalog)
        for file in json_files:
            print(f"--> parsing metadata file: {file}")
            with open(os.path.join(destination, file)) as j_file:
                j_dict = json.load(j_file)
            try:
                for products in j_dict["searchData"]["results"]["products"]:
                    for idx, image in enumerate(products["images"]):
                        if image["src"]:
                            input_data = [
                                products["productId"],
                                products["gender"],
                                products["category"],
                                products["year"],
                                products["primaryColour"],
                                products["season"],
                                image["src"],
                                idx,
                            ]
                            writer.writerow(input_data)
            except KeyError:
                continue
            del j_dict
            os.remove(os.path.join(destination, file))

    print(f"<-- saved productCatalogData to: {file_name}")


def get_image(file_loc="./data/productData.csv", img_loc="./data/images"):
    if not os.path.exists(img_loc):
        os.makedirs(img_loc)

    df = pandas.read_csv(
        file_loc,
        header=None,
        names=[
            "product_id",
            "gender",
            "category",
            "year",
            "color",
            "season",
            "image_url",
            "idx",
        ],
    )

    for gender in list(
        df.gender.unique()
    ):  # make folders per gender, category to save images respectively
        for category in df[df["gender"] == gender].category.unique():
            os.makedirs(os.path.join(img_loc, gender, category))

    mp_pool = multiprocessing.Pool(multiprocessing.cpu_count())
    for _, row in df.iterrows():
        file_ext = os.path.splitext(row["image_url"].rsplit("/", 1)[-1])[-1]
        file_name = os.path.join(
            img_loc,
            row["gender"],
            row["category"],
            str(row["product_id"]) + "_" + str(row["idx"]) + file_ext,
        )
        mp_pool.apply_async(func=_download_images, args=(row["image_url"], file_name))
    mp_pool.close()
    mp_pool.join()


if __name__ == "__main__":
    uri = ["clothing"]
    search_strings = [
        "Gender:men,men women",
        "Gender:men women,women",
        "Gender:boys boys,girls",
        "Gender:boys girls,girls",
    ]
    sort_options = ["new", "popularity", "discount", "price_desc", "price_asc"]
    page_limit = 10

    combinations = [uri, search_strings, sort_options, list(range(1, page_limit + 1))]

    fetch_metadata(combinations)  # fetch metadata & generate productCatalog
    get_image()  # download images
