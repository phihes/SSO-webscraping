#threads
from multiprocessing.dummy import Pool as ThreadPool
#processes
#from multiprocessing import Pool as ThreadPool
#pathos
#from multiprocess import Pool as ThreadPool

import logging
logger = logging.getLogger(__name__)


class ScrapePool:

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
