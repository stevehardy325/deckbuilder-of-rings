import base64
from collections import defaultdict
from enum import Enum
from io import BytesIO
import time
import requests
import os
import json
import sqlite3

from PIL import Image

max_img_cards = 69
img_rows = 7
img_cols = 10
x_res = 500
y_res = 720

class Cache:
    def __init__(self, fname) -> None:
        self.fname = fname
        self.dct = defaultdict(lambda: None)
        if os.path.exists(fname) and os.path.isfile(fname):
            with open(fname) as backing_file:
                self.dct = self.dct = defaultdict(lambda: None, json.load(backing_file))

    def lookup(self, key):
        return self.dct[key]

    def insert(self, key, value):
        self.dct[key] = value
        with open(self.fname, 'w') as backing_file:
            json.dump(self.dct,backing_file)
        
class Datatype(Enum):
    JSON=1
    BLOB=2


def requestWrapper(url, expected_datatype:Datatype=Datatype.JSON):
    time.sleep(1)
    req_return = requests.get(url)
    if expected_datatype == Datatype.JSON:
        result = req_return.json()
    elif expected_datatype == Datatype.BLOB:
        result = base64.b64encode(req_return.content).decode()
    return result


class CachedAPIHandler:
    base_url = r'https://ringsdb.com'

    def __init__(self):
        self.card_cache = Cache('cards.json')
        self.card_image_cache = Cache('card_images.json')

    def getRequest(self, path :str, values_dct: dict, cache:Cache=None, expected_datatype:Datatype=Datatype.JSON):
        unformatted_url = self.base_url + path
        print(unformatted_url)
        print(values_dct)
        formatted_url = unformatted_url.format(**values_dct)
        print(formatted_url)

        ret_val = None

        if cache is not None:
            cacheLookup = cache.lookup(formatted_url)
            if cacheLookup is not None:
                print('CACHE HIT')
                return cacheLookup
            else:
                print('CACHE MISS, WILL SAVE')
                result = requestWrapper(formatted_url, expected_datatype)
                cache.insert(formatted_url, result)
        else:
            result = requestWrapper(formatted_url, expected_datatype)
        return result

        
    def requestDeckByID(self, id: str)-> dict:
        path = r'/api/public/decklist/{decklist_id}'
        values_dct = {'decklist_id': id}
        return self.getRequest(path, values_dct)

    def requestCardByID(self, id: str,)-> dict:
        path = r'/api/public/card/{card_code}'
        values_dct = {'card_code': id}
        return self.getRequest(path, values_dct, self.card_cache)

    def requestCardImageByID(self, id: str)-> dict:
        path = r'/bundles/cards/{card_code}.png'
        values_dct = {'card_code': id}
        return self.getRequest(path, values_dct, self.card_image_cache, expected_datatype=Datatype.BLOB)

    def getCardsFromDeckByID(self, id: str):
        deck_json = self.requestDeckByID(id)
        name = deck_json['name']
        cards = []
        sideboard = []
        #for hero_id in deck_json['heroes']:
        #    cards.append(hero_id)
        for card_id in deck_json['slots']:
            cards += [card_id] * deck_json['slots'][card_id]
        for card_id in deck_json['sideslots']:
            sideboard += [card_id] * deck_json['sideslots'][card_id]

        return cards,sideboard

    

    def createTabletopSimDeckImage(self, cardlist: list, deckname, part=None):
        # Create a tabletop simulator deck template (or multiple)
        # Tabletop Sim can only handle up to 69 cards in one image, so we may need to split
        if len(cardlist) > 69:
            partitions = [cardlist[i:i+69] for i in range(0, len(cardlist), 69)]
            for i in range(len(partitions)):
                self.createTabletopSimDeckImage(partitions[i], deckname, part=i+1)
        else:
            if part is None:
                outfile_name = '{}.jpg'.format(deckname)
            else:
                outfile_name = '{}_part{}.jpg'.format(deckname, part)
            new = Image.new('RGB', (x_res*img_cols, y_res*img_rows))
            card_num = 0
            for card_id in cardlist:
                column = card_num % img_cols
                row = card_num//img_cols
                dest_x = x_res*column
                dest_y = y_res*row
                #print('{} {} {}'.format(c, dest_x, dest_y))
                img = Image.open(BytesIO(base64.b64decode(self.requestCardImageByID(card_id))))
                img = img.resize((x_res, y_res), resample=Image.LANCZOS)
                new.paste(img, (dest_x, dest_y))
                card_num += 1
            new.save(outfile_name)

    def createTabletopSimDeckImageByID(self, id: str):
        name = self.requestDeckByID(id)['name']
        cards, sideboard = self.getCardsFromDeckByID(id)
        self.createTabletopSimDeckImage(cards, name)
        if len(sideboard) > 0:
            self.createTabletopSimDeckImage(sideboard, name + ' Sideboard')


if __name__ == '__main__':
    c = CachedAPIHandler()
    c.createTabletopSimDeckImageByID(34513)
    c.createTabletopSimDeckImageByID(34514)
    c.createTabletopSimDeckImageByID(34515)
    c.createTabletopSimDeckImageByID(34516)
    



