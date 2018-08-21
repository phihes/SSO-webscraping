from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, NoSuchFrameException, TimeoutException, WebDriverException
import selenium.webdriver.support.ui as ui
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from .scrapetools import Scraper, Results
from urllib.error import URLError
import time
import logging
logger = logging.getLogger(__name__)


class ISOScraper(Scraper):

    def __init__(self, phantomjs_exec, urls):
        self.browser = webdriver.PhantomJS(
            executable_path=phantomjs_exec)
        self.urls = urls
        self.page = 0
        self.results = Results(self.urls['save_to'], save_each=True)
        try:
            self.login()
            logger.info("connection tested successfully!")
        except Exception:
            logger.error("error: connection failed!")

    def login(self):
        self.browser.get(self.urls['home'])

    def _read_page(self, waitfor="results", timeout=10, xpaths=[]):
        self.browser.execute_script("return document.body.innerHTML")  

        wait = WebDriverWait(self.browser, timeout).until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, "v-loading-indicator")))
        self.browser.execute_script("return document.body.innerHTML")        
        if waitfor=="results":
            wait2 = WebDriverWait(self.browser, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.v-slot-search-result-layout")))
            self.browser.execute_script("return document.body.innerHTML")
        elif waitfor=="std":
            wait2 = WebDriverWait(self.browser, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.notify")))
            self.browser.execute_script("return document.body.innerHTML")            
        for x in xpaths:
            wait3 = WebDriverWait(self.browser, timeout).until(
                EC.presence_of_element_located((By.XPATH, x)))
        return self.browser.execute_script("return document.body.innerHTML")

    def start_search(self):
        self.browser.get(self.urls['home'])

        self._read_page(waitfor="search")

        self.browser.find_element_by_xpath("//*[@id='gwt-uid-6']").click()
        self.browser.find_elements_by_xpath("//*[contains(@class, 'v-button-go')]")[0].click()

        btn_sort_x = "(//div[contains(@class, 'v-button-sort')])[3]"
        self._read_page(xpaths=[btn_sort_x], timeout=30)
        btn_sort = self.browser.find_element_by_xpath(btn_sort_x)
        self.browser.maximize_window()
        btn_sort.click()

        logger.info("sorted results")

        self._read_page()

        self.page += 1

    def next_page(self):
        done = False        
        #button_cnt = len(self.browser.find_elements_by_class_name('v-button-i-paging'))
        #button_pos = 0
        #if self.page==1:
        #    button_pos = 1
        #else:
        #    button_pos = self.page + 1 if self.page < 6 else 7
        #if not button_cnt == button_pos:
        logger.info("getting page " + str(self.page + 1))
        self.browser.find_element_by_xpath("//div[contains(@class, 'v-button-i-paging last')]").click()
        #self.browser.find_elements_by_xpath("//div[contains(@class, 'v-button-i-paging')]")[button_pos].click()
        self._read_page()
        self.page += 1
        #else:
        #    done = True

        return done

    def scan_page(self):
        done = False

        return done

    def _parse_std(self):
        id = self.browser.find_element_by_xpath("//div[contains(@class, 'v-label-h2')]").text
        title = self.browser.find_element_by_xpath("//div[contains(@class, 'std-title')]").text

        return [id, title]

    def get_standards(self):
        for i in range(0,10):
            self._read_page()
            std = self.browser.find_elements_by_xpath("//div[contains(@class,'v-slot-std-ref')]")[i]
            std_id = str(std.text)
            std.click()
            self._read_page(waitfor="std")
            try:
                self.results.add(std_id, self._parse_std())
                logger.info("saved results for " + std_id)
            except NoSuchElementException as e:
                pass
            self.results.to_csv(std_id)
            self.browser.get(self.urls['search'])
            self._read_page()
            #self.browser.execute_script("window.history.go(-1)")
            #self.browser.save_screenshot(self.urls['save_to'] + str(i) + '.png')


    def run(self, keywords):
        self.start_search()
        done = self.scan_page()
        x=0
        while not done and x<4:
            self.get_standards()
            # done when last page reached or all stds have been saved          
            done = self.next_page() or self.scan_page()
            x += 1

        logger.info("done scraping.")

        return self.results