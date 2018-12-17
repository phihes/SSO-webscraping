# A small webscraping framework

* uses Selenium WebDriver https://selenium-python.readthedocs.io/api.html with PhantomJS to render html from JavaScript
* multithreading: Implement a subclass `MyClass(Scraper)` of `scrapetools.Scraper` to run with `scrapetools.ScrapePool(MyClass, ...)`

Scraper UIs are implemented in IPython Notebooks.

Available scrapers:

* AFNOR: Collect meta-data on french standards from AFNOR's website (requires user+password)
* WOS: Collect authors and e-mail addresses on publication topics from web of science
* ISO: Collect ISO standards
* DIN: Collect information on all DIN committees ("Normungsausschuesse"), their sub- and mirror-committees (at ISO, CEN, ...)