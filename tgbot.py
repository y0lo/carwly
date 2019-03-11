import requests


class TGBot:
    def __init__(self, token, chat_id=None):
        self.__url = "https://api.telegram.org/bot{}/".format(token)
        self.__chat_id = chat_id
        print (self.__url)

    def __get_json(self, tg_method, *args, **kwargs):
        return requests.get(url=self.__url + tg_method, verify=False, *args, **kwargs).json()

    def __post_json(self, tg_method, *args, **kwargs):
        return requests.get(url=self.__url + tg_method, verify=False, *args, **kwargs).json()

    def get_updates(self):
        return self.__get_json(tg_method="getUpdates")

    def send_message_params(self, params, chat_id=None):
        return self.__post_json(tg_method='sendMessage', data=params)

    def send_message(self, text, chat_id=None):
        current_chat_id = chat_id if chat_id else self.__chat_id
        if not current_chat_id:
            raise ValueError("TGBot requires chat_id to send messages")
        params = {'chat_id': current_chat_id, 'text': text}
        return self.send_message_params(params)

