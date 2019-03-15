CARWLY_CONFIG = {
    'tg_bot': {
        'token': '',
        'chat_id': 0
    },

    'parser_tasks': [
        {
            'url': "https://auto.ru/...",
            'headers': {
            },
            'cookies': {
            }
        },
        {
            'url': "https://www.avito.ru/...",
            'headers' : {
            }
        }
    ],

    'car_filter_regex_str': "Nissan|Opel|Volkswagen|Octavia|Suzuki|Mitsubishi|Toyota|Mazda|KIA|Volvo|SsangYong|Dodge|Honda",
}

if __name__ == '__main__':
    print(CARWLY_CONFIG)
