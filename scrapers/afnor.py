from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, NoSuchFrameException
from .scraper import Scraper, Results
import logging
logger = logging.getLogger(__name__)


class AfnorScraper(Scraper):

    STATES_FIND_ALL = 1
    STATES_FIND_EFFECTIVE = 2
    STATES_FIND_NON_EFFECTIVE = 3

    def __init__(self, phantomjs_exec, urls, save_to, user, password,
                 states=STATES_FIND_ALL):
        self.browser = webdriver.PhantomJS(
            executable_path=phantomjs_exec)
        self.urls = urls
        self.save_to = save_to
        self.user = user
        self.password = password
        self.states = states
        try:
            self.login()
            logger.info("connection tested successfully!")
        except Exception:
            logger.error("error: connection failed!")

    def set_states(self):
        xpath = "//div[@id='Etat_child']/ul/li[position()=" + \
            str(self.states) + "]/span"
        dropdown = self.browser.find_element_by_id("Etat_title")
        dropdown.click()
        state_elem = self.browser.find_element_by_xpath(xpath)
        state_elem.click()

    def _metalemen_get_info(self, dom):
        key = dom.label.getText()
        value = dom.section.getText()

    def _extract_meta(self, word, dom, get_members=False):
        resultlist = dom.find("div", {"class": "conteneur_liste_resultat"})
        elems = resultlist.findAll("div",
                                   {"class": ["document_pair",
                                              "document_impair"]}
                                   ) if resultlist is not None else []
        meta = list()
        for std in elems:
            ref = std.find("p", {"class": "reference"})
            if ref is not None:
                self.browser.get(self.urls['base'] + ref.a.get("href"))
                content = BeautifulSoup(self.browser.execute_script(
                    "return document.body.innerHTML"))

                infoelems = content.findAll("div", {"class": ["odd", "even"]})
                info = {
                    'query': word
                }
                for e in infoelems:
                    info[e.label.getText().strip(' \t\n\r')
                         ] = e.section.getText().strip(' \t\n\r')

                for l in std.findAll("div", {"class": "document_xml"}):
                    info[l.a.get("class")[0]] = l.a.get("href")

                if get_members and "html_fr" in info.keys():
                    info["members"] = self.get_members(info["html_fr"])

                meta.append(info)

        return meta

    def _extract_links_to_html(self, dom):
        docs = dom.find_all(attrs={"class": "document_xml"})
        links = [d.a.get("href") for d in docs]
        fn = path.join(self.save_to, "links_" +
                       Results._get_safe_keyword(word) + ".csv")
        with open(fn, "w+") as f:
            print("\n".join(links), file=f)
        return links

    def login(self):
        self.browser.get(self.urls['base'])
        user = self.browser.find_element_by_id("Login")
        pwd = self.browser.find_element_by_id("Password")
        user.send_keys(self.user)
        pwd.send_keys(self.password)
        submitButton = self.browser.find_element_by_id("submitBtn")
        submitButton.click()
        nextSubmitButton = self.browser.find_element_by_id("submit")
        nextSubmitButton.click()
        nextSubmitButton = self.browser.find_element_by_id("submit")
        nextSubmitButton.click()

    def logout(self):
        self.browser.get(self.urls['base'] + self.urls['logout'])

    def search(self, word):
        x = 0
        while x < 3:
            try:
                self.browser.get(
                    self.urls['base'] + "en-US/sw/recherche/critere?crt=0")
                break
            except ConnectionResetError:
                logger.warn("connection reset while looking for " +
                            word + ", try" + str(x))
                x += 1
        if x >= 3:
            logger.warn("search for " + word +
                        " failed! (too many connections reset)")
            return False
        else:
            try:
                self.set_states()
                self.browser.find_element_by_id(
                    "Mot").send_keys("\"" + word + "\"")
                self.browser.find_element_by_id("Xml").click()
                self.browser.find_element_by_id("submit").click()
                self.browser.get(self.urls['base'] + self.urls['results'])
                return True
            except NoSuchElementException:
                logger.warn("search for " + word + " failed!")
                return False

    def get_data(self, url):
        trying = 0
        content = None

        # try to fetch content without logging in,
        # if that does not work, log in and re-try up to 2 times
        while trying < 3 and content is None:
            try:
                self.browser.get(url)
                # actual data is in an iframe
                self.browser.switch_to.frame("iFrameXml")
                content = self.browser.execute_script(
                    "return document.body.innerHTML")
            except NoSuchFrameException:
                self.login()
                trying += 1

        if content is not None:
            return BeautifulSoup(content)
        else:
            logger.warn("could not get data from " + url)
            return None

    def run(self, keywords):

        results = Results(self.save_to)

        for word in keywords:

            logger.info("logging in")
            self.login()

            logger.info("searching for " + word)
            if self.search(word):

                # step 3: get search results
                hits = BeautifulSoup(self.browser.execute_script(
                    "return document.body.innerHTML"))
                for res in self._extract_meta(word, hits, get_members=True):
                    results.add(word, res)
                results.to_csv(word)

                # logout
                self.logout()

        return results

    def load_links(self):
        all_files = glob.glob(path.join(self.save_to, "links_*.csv"))
        loaded_links = {}
        for fn in all_files:
            with open(fn) as f:
                key = Results._get_safe_keyword(path.basename(fn)[6:-4])
                loaded_links[key] = [line.rstrip('\n') for line in f]

        self.last_links = loaded_links
        return loaded_links

    def get_members(self, link):
        id = link.split('/')[5] if len(link.split('/')) >= 6 else None
        doc = self.get_data(self.urls['base'] +
                            link) if id is not None else None
        members = None
        if doc is not None:
            members = doc.find("table", class_="nrmListeMembres")

        return "|".join(
            [person.id for person in parse_people(members)]
        ) if members is not None else ""


class Person:

    def __init__(self, gender, name, group):
        self._gender = "n"
        if gender == "M":
            self._gender = "m"
        elif gender == "MME":
            self._gender = "f"
        self._name = name
        self._group = group

    @property
    def gender(self):
        return self._gender

    @property
    def name(self):
        return self._name

    @property
    def group(self):
        return self._group

    @property
    def desc(self):
        return self.name + " (" + self.gender + "), " + self.group

    @property
    def id(self):
        # return self.gender + "." + self.name.replace(" ", "-") +
        # self.group.replace(" ", "-")
        return Results._get_safe_keyword(self.name) + " : " + Results._get_safe_keyword(self.group)


def parse_people(table):
    people = []
    for row in table.find('tbody').find_all('tr'):
        people.append(Person(*[f.text for f in row.find_all('td')]))

    return people
