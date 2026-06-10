# adapted from https://github.com/mqnc/talon_german

import logging
import pickle

import requests

from speech.core.cache import get_cache_dir

# PUNCTUATION_WORDS = {
#     "punkt": ".",
#     "strich": ",",
#     "ausrufezeichen": "!",
#     "fragezeichen": "?",
#     "doppelpunkt": ":",
# }


# END_OF_SENTENCE_WORDS = {
#     "!",
#     "?",
#     ".",
# }


class GermanFormatter:
    """Format recognized text according to german orthography rules, e.g. capitalizing nouns and the first word of a sentence."""

    def __init__(self):
        self.capitalized_words: set[str] = set()

    def load(self):
        cache_dir = get_cache_dir()
        dictionary_url = (
            "https://github.com/mqnc/talon_german/raw/master/dictionary/german.dic"
        )
        dictionary_path = cache_dir / "german.dic"
        dictionary_cache_path = cache_dir / "german.pickle"
        # download dictionary if it doesn't exist
        if not dictionary_path.exists():
            logging.info("Downloading german dictionary...")
            response = requests.get(dictionary_url)
            response.raise_for_status()
            with open(dictionary_path, "wb") as file:
                file.write(response.content)
        # create fast-load cache if it doesn't exist
        if not dictionary_cache_path.exists():
            logging.info("Creating cache for german dictionary...")
            capitalized_words = set()
            with open(dictionary_path, encoding="ISO-8859-1") as file:
                for word in file:
                    if word[0].isupper():
                        capitalized_words.add(word.lower().strip())
            with open(dictionary_cache_path, "wb") as file:
                # pickle the word list
                pickle.dump(capitalized_words, file, pickle.HIGHEST_PROTOCOL)
        # load dictionary
        with open(dictionary_cache_path, "rb") as file:
            self.capitalized_words = pickle.load(file)

    def format(self, phrase: str) -> str:
        words = phrase.split()
        formatted_words = []
        for i, word in enumerate(words):
            if i == 0:
                # Uppercase first word
                formatted_words.append(
                    word[0].upper() + word[1:] if len(word) > 1 else word.upper()
                )
            elif word in self.capitalized_words:
                formatted_words.append(word[0].upper() + word[1:])
            else:
                formatted_words.append(word)
        return " ".join(formatted_words) + "."
