# Deckbuilder of Rings

This is just a simple python script designed to turn Ringsdb.com decklists downloaded in "Text File" form into Tabletop Simulator compatible deck template images for easy import. Images are generated via Pillow image composition. This should be cross-platform, but I've only built it with python 3.9 on windows so far.

To run:
	* install all requirements using pip and the included requirements.txt file
	* organize your card images as listed below
	* run `python deckbuilder-of-rings.py` and wait. Total runtime will depend on the number of decks being created, but should only take a few minutes at most

Note that this application does not include any images, names, or likenesses of the cards to be used, and no scraping capability is planned to be added. This tool will only work if you can provide the images yourself.

The directory format for card images should look something like this:
	* deckbuilder-of-rings.py
	* decks/
		* decklist1.txt
		* decklist2.txt
	* Cycle Name
		* Set Name
			* Player Cards
				* Player Card 1 Name.jpg
				* Player Card 2 Name.jpg
				* ...

Created deck images will be deposited into the ./decks/ directory. In the case that you have a deck of more than 69 cards (the Tabletop Sim limit), the deck will be split into parts. Sideboards and Mainboards will also go into separate deck images.
