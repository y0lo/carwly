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
    cars = []
    page = html.fromstring(content)
    xpath_req = "//*[contains(@class, 'catalog-list js-catalog-list clearfix')]/div/div"
    for el in page.xpath(xpath_req):
        if el.get('id') and re.search("i\d+", el.get('id')):
            if el.get('id') and re.search("i\d+", el.get('id')):
                price = el.xpath(".//*[contains(@class, 'price ')]/text()")[0]
                price = int(re.sub(' +', '', price))
                mileage = el.xpath(".//*[contains(@class, 'specific-params specific-params_block')]/text()")[0]
                mileage = re.search('(\d+)(\S+)', mileage.replace(' ', '')).group(1)
                title = el.xpath(".//*[contains(@class, 'item-description-title-link')]/span/text()")[0]
                desc_regex = re.search("(\A.+), (\d\d\d\d)", title)
                name = desc_regex.group(1)
                year = int(desc_regex.group(2))
                link = el.xpath(".//*/a[contains(@class, 'item-description-title-link')]/@href")[0]
                link = 'https://www.avito.ru' + link
                id = hash(link)
                cars.append(Car(url=link, id=int(id), name=name, price=price, mileage=mileage, year=year))
    if 0 == len(cars):
        raise ParserException(content)
    return cars


def get_parser_handler(url):
    hostname = urlparse(url).hostname
    if "auto.ru" in hostname:
       return parse_cars_autoru
    elif "avito" in hostname:
        return parse_cars_avito
    else:
        raise ValueError("Parser for {} was not defined.".format(hostname))


def car_to_str(car):
    return "{:<40} {:>10} {:>10}p {:>10}km {:<120}".format(car.name, car.year, car.price, car.mileage, car.url)


if __name__ == "__main__":
    import pickle
    import time
    import random
    import re

    from config import CARWLY_CONFIG as CONFIG
    from tgbot import TGBot

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
    postFilter = re.compile(CONFIG["car_filter_regex_str"], flags=re.I)

    # Load DB
    if os.path.isfile(DB_CARS_FILE_NAME):
        with open(DB_CARS_FILE_NAME, 'rb') as db_file:
            db_cars = pickle.Unpickler(db_file).load()
            logger.info("DB file is opened: " + DB_CARS_FILE_NAME)

    #Init Bot

    bot = TGBot(token=CONFIG['tg_bot']['token'])

    bot_params = {'chat_id': CONFIG['tg_bot']['chat_id'],
                  'parse_mode': 'Markdown',
                  'disable_web_page_preview': True
                  }
    bot_text_template = "[{name}]({link})\r\n{price}p\r\n{year}\r\n{mileage}km"

    try:
        logger.info("Started: " + str(datetime.datetime.now()))

        tasks = []
        for task_cfg in CONFIG['parser_tasks']:
            tasks.append(Search(
                task_cfg['url'],
                partial(requests.get,
                        verify=False,
                        headers=task_cfg['headers'] if 'headers' in task_cfg else None,
                        cookies=task_cfg['cookies'] if 'cookies' in task_cfg else None
                        ),
                get_parser_handler(task_cfg['url'])
            ))
            #Log session data
            logger.info("Link: " + str(task_cfg['url']))

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
                            print("{:<5} {}".format(new_car_counter, car_to_str(car)))
                            bot_params['text'] = bot_text_template.format(
                                name=car.name,
                                link=car.url,
                                price=car.price,
                                year=car.year,
                                mileage=car.mileage)
                            bot.send_message_params(params=bot_params)

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

