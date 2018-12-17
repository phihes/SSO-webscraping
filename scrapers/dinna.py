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


class DinNaScraper(Scraper):

	def __init__(self, phantomjs_exec, urls, nas):
		self.browser = webdriver.PhantomJS(
			executable_path=phantomjs_exec)
		self.urls = urls
		self.nas = nas.to_dict(orient='index')
		try:
			self.login()
			logger.info("connection tested successfully!")
		except Exception:
			logger.error("error: connection failed!")


	def login(self):
		self.browser.get(self.nas[list(self.nas.keys())[0]]['link'])

	def run(self, keywords):

		results = Results(self.urls['save_to'])

		for na in keywords:
			data = self.search(na)
			results.add(na, data)
			results.to_csv(na)

		return results

	def _add(self, original, new):
		return {k: v.extend(new[k]) for k,v in original.items()}

	def search(self, na):
		data = {
			"ids": [na],
			"links": [self.nas[na]["link"]],
			"names": [self.nas[na]["name"]],
			"parents": [None],
			"types": ["Normenausschuss"],
			"mirrors": [None]
		}
		
		self._add(data, self.get_na_subs(
			link=self.nas[na]["link"] + "/nationale-gremien",
			parent=na,
			subtype='nationale-gremien'
		))
		self._add(data, self.get_na_subs(
			link=self.nas[na]["link"] + "/europaeische-gremien",
			parent=na,
			subtype='europaeische-gremien'
		))
		self._add(data, self.get_na_subs(
			link=self.nas[na]["link"] + "/internationale-gremien",
			parent=na,
			subtype='internationale-gremien'
		))

		return data


	def get_na_subs(self, link, parent, subtype, level=1):
		subs = {
			"ids": [],
			"names": [],
			#subtype + "-subcommittees": [],
			"links": [],
			"parents": [],
			"types": [],
			"mirrors": []
		}
		print("looking for {} at {}".format(parent, link))
		try:
			self.browser.get(link)
			content = self.browser.execute_script(
						 "return document.body.innerHTML")

			doc = WebDriverWait(self.browser, 10).until(
				EC.presence_of_element_located((By.ID, "etracker")))

			if level==1:
				t_xpath = "/html/body/div[3]/main/div[5]/div/div/form[2]/table/tbody"
			else:
				t_xpath = "/html/body/div[3]/main/div[4]/div/div[1]/table/tbody"
			
			try:
				table = doc.find_elements_by_xpath(t_xpath)[0]
			except IndexError:
				return subs

			subsub_queue = []

			for row in table.find_elements_by_xpath(".//tr"):
			# /html/body/div[3]/main/div[5]/div/div/form[2]/table/tbody/tr[1]/td[1]/span/a

				lines = row.text.split("\n")
				c_id = lines[1]
				c_name = lines[3]
				c_mirror = None
				c_link = row.find_elements_by_tag_name("a")[0].get_attribute("href")
				if subtype in ["internationale-gremien", "europaeische-gremien"] and len(lines)>8:
					c_name = lines[4]
					c_mirror = lines[8]			
				subs["ids"].append(c_id)
				subs["links"].append(c_link)
				subs["names"].append(c_name)
				subs["parents"].append(parent)
				subs["types"].append(subtype)
				subs["mirrors"].append(c_mirror)

				if level<2:
					subsub_queue.append({
						"link": c_link,
						"parent": c_id,
						"subtype": subtype,
						"level": 2
					})

			pages = doc.find_elements_by_xpath('//a[@class="pagination-link"]')
			if len(pages)>0 and pages[-1].get_attribute("href") != link:
				subsub_queue.append({
					"link": pages[-1].get_attribute("href"),
					"parent": parent,
					"subtype": subtype,
					"level": level
				})					

			for args in subsub_queue:
				for k, v in self.get_na_subs(**args).items():
					subs[k].extend(v)

		except NoSuchElementException as e:
			logger.warning("Could not find sub info for {}".format(parent))
			return subs
		except TimeoutException:
			logger.warn('timeout while looking for subs of {}, on {}'.format(parent, link))
			return subs

		return subs

	def get_na_main(self, na):
		main = {}
		try:
			self.browser.get(self.nas[na]["link"])
			content = self.browser.execute_script(
						 "return document.body.innerHTML")

			doc = WebDriverWait(self.browser, 10).until(
				EC.presence_of_element_located((By.ID, "reg-salutation-M")))

			# description text
			main["description"] = doc.find_elements_by_xpath(
				"/html/body/div[3]/main/div[4]/div/div[1]/div/p[1]")[0].text

			# head (responsible person)
			main["head"] = doc.find_elements_by_xpath(
				"/html/body/div[3]/main/div[4]/div/div[2]/div[1]/div[1]/div[3]/h1")[0].text

		except NoSuchElementException as e:
			logger.warning("Could not find main info for {}".format(na))
			return main
		except TimeoutException:
			logger.warn('timeout while looking for {}'.format(na))
			return main

		return main

