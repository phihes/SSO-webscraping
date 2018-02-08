from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, NoSuchFrameException, TimeoutException, WebDriverException
import selenium.webdriver.support.ui as ui
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from .scrapetools import Scraper, Results
from urllib.error import URLError
import logging
logger = logging.getLogger(__name__)

class WosScraper(Scraper):

    def __init__(self, phantomjs_exec, urls, topic, num_pubs):
        self.browser = webdriver.PhantomJS(
            executable_path=phantomjs_exec)
        self.urls = urls
        self.topic = topic
        self.num_pubs = num_pubs
        try:
            self.login()
            logger.info("connection tested successfully!")
        except Exception:
            logger.error("error: connection failed!")

    def login(self):
        self.browser.get(self.urls['author_search'] + "test")

    def _extract_emails(self, num_pubs, browser):
        pub_urls = []
        results = []
        for i in range(1, num_pubs):
            try:
                pub_urls.append(
                    browser.find_elements_by_xpath(
                        "//div[@id='RECORD_" + str(i) +"']//a")[0].get_attribute("href")
                )
            except IndexError:
                pass
            except NoSuchElementException as e:
                pass

        for url in pub_urls:
            try:
                browser.get(url)
                doc = WebDriverWait(self.browser, 10).until(
                    lambda b: b.find_element_by_class_name('FR_field'))
                emails = doc.find_elements_by_xpath("//a[starts-with(@href, 'mailto:')]")
                results.extend(e.get_attribute("href").split(":")[1] for e in list(emails))
            except NoSuchElementException as e:
                pass
            except TimeoutException:
                pass
            except IndexError:
                pass

        return results


    def search(self, author):
        try:
            self.browser.get(self.urls['author_search'] + author)
            content = self.browser.execute_script(
                         "return document.body.innerHTML") 
            """
            first = WebDriverWait(self.browser, 300).until(
                EC.presence_of_element_located((By.ID, "UA_output_input_form")))
            content = self.browser.execute_script(
                         "return document.body.innerHTML")

            self.browser.find_element_by_xpath(
                "//*[@id='chunk_data']/tbody/tr[4]/td/div/table[2]/tbody/tr[2]/td[1]/input").click()
            self.browser.find_element_by_xpath(
                "//*[@id='chunk_data']/tbody/tr[4]/td/div/table[1]/tbody/tr[1]/td[2]/input[1]").click()"""
            second = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.ID, "sws")))

            content = self.browser.execute_script(
                         "return document.body.innerHTML")            
            
            ## added keyword search:
            self.browser.find_element_by_xpath("//*[@id='sws']").send_keys(self.topic)
            self.browser.find_element_by_xpath("//*[@id='refine_form']").submit()
            wait_for_results = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.ID, "RECORD_1")))    

            content = self.browser.execute_script(
                         "return document.body.innerHTML")

            emails = self._extract_emails(self.num_pubs, self.browser)

            return list(set(emails))

        except NoSuchElementException as e:
            logger.warn('something went wrong while looking for ' + author)
            #logger.warn(e)
            return []
        except TimeoutException:
            logger.warn('timeout while looking for ' + author)
            return []
        except WebDriverException:
            self.login()
            self.search(author)
        

    def run(self, keywords):

        results = Results(self.urls['save_to'])

        for k in keywords:
            e = self.search(k)
            logger.info("found " + str(len(e)) +
                        " addresses for " + k + ": " + ", ".join(e))
            results.add(k, e)
            results.to_csv(k)



        return results
