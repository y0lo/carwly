import requests


class TelegramError(Exception):
    pass


class TelegramBot:
    def __init__(self, token, chat_id=None):
        self.__url = "https://api.telegram.org/bot{}/".format(token)
        self.__chat_id = chat_id
        self.__proxies = {
            #'http': 'http://proxy.antizapret.prostovpn.org:3128',
        }
        print (self.__url)

    @staticmethod
    def _parse(data):
        if not data['ok']:
            if data['description']:
                return data['description']
            raise TelegramError("Unknown response")
        return data['result']

    def _request(self, tg_method, *args, **kwargs):
        try:
            resp = requests.post(url=self.__url + tg_method, verify=False, proxies=self.__proxies, *args, **kwargs)
        except requests.Timeout:
            return []
        except:
            raise TelegramError("HTTP error")

        if 200 <= resp.status_code <= 299:
            try:
                data = resp.json()
            except ValueError:
                raise TelegramError("Can't decode JSON response")
        else:
            raise TelegramError("Error HTTP status {}".format(resp.status_code))
        return self._parse(data)

    def get_updates(self):
        return self._request(tg_method="getUpdates")

    def get_updates_poll(self, offset=None, timeout=20, limit=100, allowed_updates=[]):
        data = {
            'timeout': int(timeout),
            'limit': int(limit),
        }
        if offset:
            data['offset'] = int(offset)
        if len(allowed_updates):
            data['allowed_updates'] = allowed_updates
        return self._request(tg_method="getUpdates", timeout=timeout, data=data)

    def send_message(self,
                     text,
                     chat_id=None,
                     parse_mode=None,
                     disable_web_page_preview=True,
                     disable_notification=False,
                     reply_to_message_id=None,
                     reply_markup=None):
        current_chat_id = chat_id if chat_id else self.__chat_id
        if not current_chat_id:
            raise ValueError("TGBot requires chat_id to send messages")

        params = {
            'chat_id': current_chat_id,
            'text': text,
            'disable_web_page_preview': disable_web_page_preview,
            'disable_notification': disable_notification
        }
        if parse_mode:
            params['parse_mode'] = parse_mode
        if reply_to_message_id:
            params['reply_to_message_id'] = reply_to_message_id
        if reply_markup:
            params['reply_markup'] = reply_markup

        return self._request(tg_method='sendMessage', data=params)

if __name__ == "__main__":

    requests.packages.urllib3.disable_warnings()

    try:
        bot = TelegramBot(token="")
        resp = bot.get_updates()
        print(resp)
        if len(resp) and resp[0]['update_id']:
            resp = resp[0]
            bot.send_message(text = "Hello {}. I'm waiting a msg".format(resp['message']['from']['first_name']), chat_id=resp['message']['chat']['id'])
            n_resp = bot.get_updates_poll(offset=resp['update_id']+1)
            if len(n_resp) and n_resp[0]['update_id'] != resp['update_id']:
                n_resp = n_resp[0]
                bot.send_message(text = "Msg {}".format(n_resp['message']['text']), chat_id=resp['message']['chat']['id'])
            else:
                bot.send_message(text = "Timeout", chat_id=resp['message']['chat']['id'])
    except TelegramError as e:
        print(str(e))

    #bot.send_message(text="**Hello**", parse_mode="Markdown")
