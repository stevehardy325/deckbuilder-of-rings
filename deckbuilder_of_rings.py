import glob
import os
import os.path
import sqlite3
import re
from PIL import Image

max_img_cards = 69
img_rows = 7
img_cols = 10
x_res = 500
y_res = 720
#x_res = 250
#y_res = 350

# Utility Functions

def normalizeString(text: str):
    # remove accents from text string for easier globbing in filesystem
    map = {'í': 'i', 'ó': 'o', 'á': 'a', 'û': 'u',
           'ú': 'u', 'é': 'e', '_': '', '\'': ''}
    lowered = text.lower()
    for key in map:
        lowered = lowered.replace(key, map[key])
    return lowered.strip()


def splitIdFromPath(text: str):
    # split off anything before the first " - " instance
    separated = text.split(' - ')

    if separated is None or len(separated) == 0:
        return None, None
    elif len(separated) == 1:
        return None, separated[0]
    elif len(separated) == 2:
        return separated[0], separated[1]
    else:
        return separated[0], ' - '.join(separated[1:])


class Card:
    # card object - contains basic lookup information like name and set, along with path to the image file on disk

    def __init__(self, name: str, setname: str, set_card_id: int, cardtype: str, image_path: str, image: bytes = None) -> 'Card':
        self.name = normalizeString(name)
        self.setname = normalizeString(setname)
        self.image_path = image_path
        self.set_card_id = set_card_id
        self.cardtype = cardtype

    @classmethod
    def fromPath(cls, path: str) -> 'Card':
        # returns a Card object based on a file path from the current root
        parts = path.split('\\')

        # we'll do the "set" lookup later using wildcard matching, so including all directories is fine for now
        setname = '-'.join(parts[0:-1])

        # treat the cardname as the filename (last in split path list), but remove any ID numbers or file extensions
        raw_cardname = parts[-1].split('.')[0]
        cardid, cardname = splitIdFromPath(raw_cardname)

        # cardtype can be anywhere in the path, so check them all
        raw_type = parts[1:len(parts) - 1]
        cardtype = None
        for t in ['Player', 'Encounter', 'Quest', 'Nightmare']:
            if t in parts[0:-1]:
                cardtype = t
                break
        c = Card(cardname, setname, cardid, cardtype, path)
        return c

    def __repr__(self) -> str:
        outstr = '{} ({}, {}) @ {}'.format(self.name, self.setname,
                                           self.cardtype, self.image_path)
        return outstr

    def getFileContents(self) -> bytes:
        # return a bytes object corresponding to the image file that this card points to
        data = None
        # with open(self.image_path, 'rb') as file:
        #    data = file.read()
        return data

    def toTuple(self) -> tuple[str, str, str, int, str]:
        # return a tuple of name, setname, cardtype, set_card_id, image_path, and file contents blob
        # useful for database dump, no need to convert in the database object

        return (self.name, self.setname, self.cardtype, self.set_card_id, self.image_path, self.getFileContents())


class CardDatabaseHandler:
    # wrapper to handle storing the cards in a sqlite3 database, including insertion, and querying

    insert_statement = 'insert into cards (name, setname, cardtype, set_card_id, image_path, image) values (?, ?, ?, ?, ?, ?)'
    select_statement = "select name, setname, cardtype, set_card_id, image_path, image from cards where name like ? and setname like ?"

    def __init__(self, db_fname: str = 'cards.db'):
        self.filename = db_fname
        with sqlite3.connect(self.filename) as conn:
            conn.execute('drop table if exists cards')
            conn.execute('''
                create table if not exists cards (
                    setname text,
                    set_card_id integer,
                    name text,
                    cardtype text,
                    image_path text,
                    image blob,
                    primary key (setname, name, set_card_id, image_path)
                )
                ''')

    def addCard(self, card: Card) -> None:
        # insert one Card object into the database

        with sqlite3.connect(self.filename) as conn:
            conn.execute(self.insert_statement, card.toTuple())

    def addCards(self, cards: list[Card]) -> None:
        # insert multiple Card objects into the database, using executemany for speedup

        cardsAsTuples = [c.toTuple() for c in cards]
        with sqlite3.connect(self.filename) as conn:
            conn.executemany(self.insert_statement, cardsAsTuples)

    def lookupCards(self, cardname: str, setname: str) -> list[Card]:
        # return a list of possible cards matching the exact cardname, and having setname somewhere in the set path

        cards = []
        with sqlite3.connect(self.filename) as conn:
            cur = conn.execute(self.select_statement,
                               (cardname, '%{}%'.format(setname)))
            for name, setname, cardtype, set_card_id, image_path, image in cur.fetchall():
                cards += [Card(name, setname, set_card_id,
                               cardtype, image_path, image)]
        return cards


def createTabletopSimDeckImage(cardlist: list[Card], deckname, part=None):
    # Create a tabletop simulator deck template (or multiple)
    # Tabletop Sim can only handle up to 69 cards in one image, so we may need to split
    if len(cardlist) > 69:
        partitions = [cardlist[i:i+69] for i in range(0, len(cardlist), 69)]
        for i in range(len(partitions)):
            createTabletopSimDeckImage(partitions[i], deckname, part=i+1)
    else:
        if part is None:
            outfile_name = './decks/{}.jpg'.format(deckname)
        else:
            outfile_name = './decks/{}_part{}.jpg'.format(deckname, part)
        new = Image.new('RGB', (x_res*img_cols, y_res*img_rows))
        card_num = 0
        for c in cardlist:
            column = card_num % img_cols
            row = card_num//img_cols
            dest_x = x_res*column
            dest_y = y_res*row
            #print('{} {} {}'.format(c, dest_x, dest_y))
            img = Image.open(c.image_path)
            img = img.resize((x_res, y_res), resample=Image.LANCZOS)
            new.paste(img, (dest_x, dest_y))
            card_num += 1
        new.save(outfile_name)


class Deck:
    image_str_fmt = '{}_{}'
    card_format_regex = re.compile('(\\d+)x (.+) \\((.+)\\)')

    def __init__(self, name, deck, sideboard):
        self.name = name
        self.deck = deck
        self.sideboard = sideboard

    def __repr__(self):
        return '{} {} {}'.format(self.name, self.deck, self.sideboard)

    def createImages(self):
        main_fname = self.image_str_fmt.format(self.name, 'main')
        createTabletopSimDeckImage(self.deck, main_fname)
        if len(self.sideboard) > 0:
            sb_fname = self.image_str_fmt.format(self.name, 'sideboard')
            createTabletopSimDeckImage(self.sideboard, sb_fname)

    @classmethod
    def getCardsFromText(cls, txt, db):
        cards = []
        matches = Deck.card_format_regex.findall(txt)
        print('Found ', len(matches), ' cards')
        for count, name, setname in matches:
            try:
                print(count, name, setname)
                card = db.lookupCards(name, setname)[0]
                print(card)
                cards += [card] * int(count)
            except Exception as e:
                print('ERROR', e)
                input()
        return cards

    @classmethod
    def fromFile(cls, fname: str, carddatabase):
        text = ''
        with open(fname, encoding="utf-8") as fobj:
            text = fobj.read()
        lines = [normalizeString(l)
                 for l in text.splitlines()]
        name = lines[0]
        if 'sideboard' in lines:
            splitLocation = lines.index('sideboard')
            main_list = lines[0:splitLocation]
            sb_list = lines[splitLocation:]
        else:
            main_list = lines
            sb_list = []

        main_list_txt = '\n'.join(main_list)
        sb_list_txt = '\n'.join(sb_list)
        main_cards = Deck.getCardsFromText(main_list_txt, carddatabase)
        sb_cards = Deck.getCardsFromText(sb_list_txt, carddatabase)
        return Deck(name, main_cards, sb_cards)


def getAllCardsFromFilesystem():
    all_card_image_files = []
    for root, dirs, files in os.walk('.'):
        for f in files:
            if '.jpg' in f:
                abs_path = os.path.join(root, f)
                all_card_image_files.append(abs_path)
    cards = [Card.fromPath(f) for f in all_card_image_files]
    return cards


if __name__ == '__main__':
    cards = getAllCardsFromFilesystem()
    dbh = CardDatabaseHandler()
    dbh.addCards(cards)
    for deckfile in glob.glob('./decks/*.txt'):
        deck = Deck.fromFile(deckfile, dbh)
        deck.createImages()
