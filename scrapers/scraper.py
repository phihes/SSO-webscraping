import pandas as pd
from os import path
import datetime
import glob
from multiprocessing.dummy import Pool as ThreadPool
import abc
import logging
logger = logging.getLogger(__name__)


class Scraper(object, metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def run(self, keywords):
        raise NotImplementedError('must define run() to use this base class')


class ScraperPool:

    def __init__(self, scraperCls, keywords, args, chunk_size=10):
        n = max(1, chunk_size)
        self.pool = ThreadPool()
        self.scrapers = self.pool.map(
            lambda x: {
                'scraper': scraperCls(**args),
                'keywords': x
            },
            [keywords[i:i + n] for i in range(0, len(keywords), n)]
        )

    def run(self):
        results = self.pool.map(
            lambda x: x['scraper'].run(
                keywords=x['keywords']
            ),
            self.scrapers
        )
        self.pool.close()
        self.pool.join()

        return results


class Results:

    SAFE_TO_ORIGINAL = 1
    ORIGINAL_TO_SAFE = 2
    #KEEP_CHARACTERS = (' ', '.', '_', '-', '#', '+', '=')
    REPLACE_CHARACTERS = {
        '/', '#',
        ':', '='
    }
    DEL_NON_ALPHANUM = False


    def __init__(self, save_to_path=None, save_each=False):
        self._results = dict()
        self._path = save_to_path
        self._save_each = save_each
        self._sep = ";"

    @staticmethod
    def _translate(keyword, translation=ORIGINAL_TO_SAFE):
        if translation == ORIGINAL_TO_SAFE:
            return Results._get_safe_keyword(keyword)
        if translation == SAFE_TO_ORIGINAL:
            return Results._get_original_keyword(keyword)

    @staticmethod
    def _get_original_keyword(safe_keyword):
        for key, val in REPLACE_CHARACTERS.items():
            keyword = keyword.replace(value, key)

        return keyword

    @staticmethod
    def _get_safe_keyword(keyword):
        for key, val in REPLACE_CHARACTERS.items():
            keyword = keyword.replace(key, value)

        if DEL_NON_ALPHANUM:
            return "".join(c for c in keyword
                           if c.isalnum() or c in KEEP_CHARACTERS).rstrip()
        else:
            return keyword

    def _get_path(self, keyword, extension=".csv"):
        t = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        return path.join(self._path,
                         self._get_safe_keyword(keyword) + "_" + t + extension)

    def _to_csv(self, keyword):
        if keyword in self._results.keys():
            df = pd.DataFrame(self._results[keyword])
            df.to_csv(self._get_path(keyword), sep=self._sep,
                      index=False, quotechar='"', quoting=csv.QUOTE_ALL)
        else:
            open(self._get_path(keyword, extension=".notfound"), 'a').close()

    def reset(self, keyword):
        self._results[keyword] = list()

    def add(self, keyword, data):
        if keyword not in self._results:
            self._results[keyword] = [data]
        else:
            self._results[keyword].append(data)

    def to_csv(self, keyword=None, save=True):
        if save and self._path is not None:
            if keyword is not None:
                self._to_csv(keyword)
            else:
                for key, _ in self._results.items():
                    self._to_csv(key)
        elif not save:
            pass

    def df(self, keyword):
        return pd.DataFrame(self._results[keyword])
