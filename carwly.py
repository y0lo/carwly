import logging
from urllib.parse import urlparse
from functools import partial
from lxml import html
import requests
import datetime
import os


class Car:
    __cache__ = dict()

    def __init__(self, url, **kwargs):
        self.url = str(url)
        prop_defaults = {
            "name": "",
            "model": "",
            "price": 0,
            "year": 0,
            "mileage": 0,
            "body_type": "",
            "engine_type": "",
            "displacement": 0,
            "transmission": "",
            "owners": 0,
            "wheel_type": "left",
            "power": 0,
            "description": "",
            "color":  "",
        }
        for (prop, default) in prop_defaults.items():
            setattr(self, prop, kwargs.get(prop, default))

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def __hash__(self):
        return hash(self.url)


class ParserException(ValueError):
    def __init__(self, content):
        self.content = content


class Search:
    def __init__(self, url, request, parser):
        self.url = url
        self.__request = request
        self.__parser = parser

    def getObjets(self):
        objects = []
        try:
            resp = self.__request(url=self.url)
            if resp.status_code == 200:
                objects = self.__parser((resp.content))
        except requests.RequestException:
            logger.warning("HTTP Request error\n\tURL: " + self.url)
            logger.debug("", exec_info=True)
        except ParserException as e:
            site_name = urlparse(self.url).hostname
            logger.warning("Parser error\n\tURL: " + self.url)
            log_path = LOG_DIR + "/" + site_name
            if not os.path.exists(log_path):
                os.makedirs(log_path)
            file_name = log_path + "/" + datetime.datetime.now().strftime("%Y%m%d_%H%M") + ".html"
            logger.warning("Backup file: " + file_name)
            f = open(file_name, 'wb')
            f.write(e.content)
            f.close()
        return objects


def parse_cars_autoru(content):
    cars = []
    page = html.fromstring(content)
    xpath_req = "//*[contains(@class, 'ListingItemSequential-module__container')]"
    for el in page.xpath(xpath_req):
        price = el.xpath(".//*[contains(@class, 'ListingItemPrice-module__content')]/text()")[0]
        price = int(re.sub('[\D]', '', price))
        mileage = el.xpath(".//*[contains(@class, 'ListingItemSequential-module__kmAge')]/text()")[0]
        mileage = int(re.sub('[\D]', '', mileage))
        title = ''#el.xpath("")[0]
        year = el.xpath(".//*[contains(@class, 'ListingItemSequential-module__year')]/text()")[0]
        name = el.xpath(".//*[contains(@class, 'Link ListingItemTitle-module__link')]/text()")[0]
        link = el.xpath(".//*[contains(@class, 'Link ListingItemTitle-module__link')]/@href")[0]#iel.xpath("./div[contains(@class, 'photo')]/a/@href")[0]
        id = hash(link)
        #link = 'https://auto.ru' + link
        cars.append(Car(url=link, id=int(id), name=name, price=price, mileage=mileage, year=year))
    if 0 == len(cars):
        raise ParserException(content)
    return cars


def parse_cars_avito(content):
    pass


search_autoru = Search(
    "https://auto.ru/sankt-peterburg/cars/vendor15/used/?year_from=2007&price_to=600000&displacement_from=1600&seller_group=PRIVATE&owners_count_group=ONE&transmission=MECHANICAL&transmission=AUTOMATIC&transmission=VARIATOR&body_type_group=ALLROAD_5_DOORS&body_type_group=LIFTBACK&body_type_group=WAGON&body_type_group=HATCHBACK_5_DOORS&body_type_group=MINIVAN&sort=cr_date-desc&output_type=table&page=1",
    partial(requests.get, verify=False, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3477.0 Safari/537.36',
        'Cache-Control': 'max-age=0',
        'Connection': 'keep-alive',
        'Accept-Language': 'en-US,en;q=0.9',
        'Referer': 'https://auto.ru/?from=wizard.brand&utm_source=auto_wizard&utm_medium=desktop&utm_campaign=common&utm_content=listing&utm_term=%D0%B0%D0%B2%D1%82%D0%BE%D1%80%D1%83&geo_id=2'
    }, cookies={
        "from_lifetime": "1542209996487",
        "from": "direct",
        "autoru_sid": "a%3Ag5bec41cc2052uv2gdl6gfk4jfk80nl9.32e00ee7e20e3f3eb1453226702ee924%7C1542209996492.604800.MEhrmwvzWh9mxCvLIIUqqg.I0KxVTkTyZGQkNygOE52MB1rsAGvE7rlZy6zAFUqKfo",
        "autoruuid": "g5bec41cc2052uv2gdl6gfk4jfk80nl9.32e00ee7e20e3f3eb1453226702ee924",
        "gdpr": "1", "X-Vertis-DC": "myt",
        "spravka": "dD0xNTQyMjEwMTg5O2k9ODQuNDcuMTg5Ljc5O3U9MTU0MjIxMDE4OTY2MjYwMDEwMTtoPTAxY2I3MWYzMzAzOTI2NjNkNjg1NTc1YWFmZjUzNTM3"
    }),
    parse_cars_autoru
)

def carToStr(car):
    return "{:<40} {:>10} {:>10}p {:>10}km {:<120}".format(car.name, car.year, car.price, car.mileage, car.url)

if __name__ == "__main__":
    import pickle
    import time
    import random
    import re

    DB_CARS_FILE_NAME = "./cars.pickle"
    LOG_DIR = "./log"

    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    logging.basicConfig(filename=LOG_DIR + "/log.txt", level=logging.WARNING)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    try:
        requests.packages.urllib3.disable_warnings()
    except ImportError:
        logger.warning("Can't config urllib3 warnings")

    db_cars = set()
    new_car_counter = 0
    postFilter = re.compile("Nissan|Opel|Volkswagen|Skoda|Suzuki|Mitsubishi|Toyota|Mazda|KIA|Volvo|Kyron", flags=re.I)

    # Load DB
    if os.path.isfile(DB_CARS_FILE_NAME):
        with open(DB_CARS_FILE_NAME, 'rb') as db_file:
            db_cars = pickle.Unpickler(db_file).load()
            logger.info("DB file is opened: " + DB_CARS_FILE_NAME)

    try:
        tasks = [search_autoru]

        #Log session data
        logger.info("Started: " + str(datetime.datetime.now()))
        for task in tasks:
            logger.info("Link: " + str(task.url))

        while True:
            for task in tasks:
                cars = task.getObjets()
                for car in cars:
                    if car in db_cars:
                        pass # check if price or milage were updated
                    else:
                        new_car_counter += 1
                        db_cars.add(car)
                        # Show if suitable
                        if postFilter.match(car.name):
                            print("{:<5} {}".format(new_car_counter, carToStr(car)))
            # Polling interval
            time.sleep(60 + random.randint(1, 40))

    except (KeyboardInterrupt, SystemExit):
        print("End")
        raise
    finally:
        with open(DB_CARS_FILE_NAME, "wb") as db_file:
            pickle.Pickler(db_file).dump(db_cars)
            logger.info("DB file is saved: " + DB_CARS_FILE_NAME)
            logger.info("Found cars {} total {}".format(new_car_counter, len(db_cars)))

