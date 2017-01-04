from os import path
import json
import mwparserfromhell as wparser
import pywikibot
import re
import wikidataStuff.helpers as helpers
from importer_utils import *

MAPPING_DIR = "mappings"
ADM0 = load_json(path.join(MAPPING_DIR, "adm0.json"))
PROPS = load_json(path.join(MAPPING_DIR, "props_general.json"))


class Monument(object):

    def get_wikilinks(self, text):
        parsed = wparser.parse(text)
        return parsed.filter_wikilinks()

    def q_from_wikipedia(self, language, page_title):
        site = pywikibot.Site(language, "wikipedia")
        page = pywikibot.Page(site, page_title)
        if page.exists():
            if page.isRedirectPage():
                page = page.getRedirectTarget()
            try:
                item = pywikibot.ItemPage.fromPage(page)
                return item.getID()
            except pywikibot.NoPage:
                print("Failed to get page for {} - {}."
                      "It probably does not exist.".format(
                          language, page_title)
                      )
                return

    def print_wd(self):
        print(
            json.dumps(self.wd_item,
                       sort_keys=True,
                       indent=4,
                       ensure_ascii=False)
        )

    def remove_markup(self, string):
        remove_br = re.compile('\W*<br.*?>\W*', re.I)
        string = remove_br.sub(' ', string)
        if "[" in string:
            string = wparser.parse(string)
            string = string.strip_code()
        return string.strip()

    def set_country(self):
        country = [item["item"]
                   for item in ADM0 if item["code"].lower() == self.adm0]
        self.wd_item["statements"][PROPS["country"]] = country

    def set_is(self, mapping):
        default_is = mapping.file_content["default_is"]
        self.wd_item["statements"][PROPS["is"]] = [default_is["item"]]

    def set_labels(self):
        self.wd_item["labels"] = {self.lang: self.remove_markup(self.name)}

    def set_heritage(self, mapping):
        heritage = mapping.file_content["heritage"]
        self.wd_item["statements"][PROPS["heritage_status"]] = helpers.listify(
            heritage["item"])

    def set_coords(self):
        if self.lat and self.lon:
            self.wd_item["statements"][PROPS["coordinates"]] = helpers.listify(
                (self.lat, self.lon))

    def set_image(self):
        if self.image:
            self.wd_item["statements"][PROPS["image"]] = self.image

    def set_commonscat(self):
        if self.commonscat:
            self.wd_item["statements"][PROPS["commonscat"]] = self.commonscat

    def exists(self, mapping):
        self.wd_item["wd-item"] = None
        if self.monument_article:
            wd_item = self.q_from_wikipedia(self.lang, self.monument_article)
            self.wd_item["wd-item"] = wd_item

    def construct_wd_item(self, mapping, data_files=None):
        self.wd_item = {}
        self.wd_item["statements"] = {}
        self.set_labels()
        self.set_country()
        self.set_is(mapping)
        self.set_heritage(mapping)
        self.set_coords()
        self.set_image()
        self.set_commonscat()
        # self.exists(mapping)

    def __init__(self, db_row_dict, mapping, data_files):
        for k, v in db_row_dict.items():
            if not k.startswith("m_spec."):
                setattr(self, k.replace("-", "_"), v)
        self.construct_wd_item(mapping)
        self.data_files = data_files

    def get_fields(self):
        return sorted(list(self.__dict__.keys()))


class SeFornminSv(Monument):

    def update_labels(self):
        if len(self.namn) == 0:
            self.wd_item["labels"][self.lang] = self.raa_nr
        else:
            self.wd_item["labels"][self.lang] = self.namn

    def set_descriptions(self):
        DESC_BASE = "fornminne"
        if len(self.typ) > 0:
            self.wd_item["descriptions"] = {"sv": self.typ.lower()}
        else:
            self.wd_item["descriptions"] = {"sv": DESC_BASE}
        self.wd_item["descriptions"]["sv"] += " i " + self.landskap

    def set_raa(self):
        self.wd_item["statements"][
            PROPS["raa-nr"]] = helpers.listify(self.raa_nr)

    def set_adm_location(self):
        municip_dict = load_json(path.join(
            MAPPING_DIR, "sweden_municipalities.json"))
        pattern_en = self.adm2.lower() + " municipality"
        try:
            municipality = [x["item"] for x in municip_dict if x[
                "en"].lower() == pattern_en][0]
            # TODO: Check if target item is valid municipality
            # I guess this could be done on the adding stage?
            self.wd_item["statements"][
                PROPS["located_adm"]] = helpers.listify(municipality)
        except IndexError:
            print("Could not parse municipality: {}.".format(self.adm2))
            return

    def set_type(self):
        if self.typ:
            table = self.data_files["types"]["mappings"]
            type_to_search_for = self.typ.lower()
            try:
                special_type = [table[x]["items"]
                                for x in table
                                if x.lower() == type_to_search_for][0]
                self.wd_item["statements"]["P31"] = special_type
            except IndexError:
                return

    def set_location(self):
        # TODO: check self.address (same as self.plats) and map it to P276.
        # This only makes sense if it's a wikilinked item,
        # and also if there's exactly 1 item
        # because stuff like
        # [[Sundsbruk]] - [[Sköns Prästbord]] (Nordväst om [[Sköns kyrka]])
        # NOTE: adm3 always empty for this table
        # ALSO if not wikilinked, check if it could be a settlement in the
        # datafile
        if self.address:
            if "[[" in self.address:
                wikilinks = self.get_wikilinks(self.address)
                if len(wikilinks) == 1:
                    target_page = wikilinks[0].title
                    print(self.address)
                    print(target_page)
                    wd_item = self.q_from_wikipedia(self.lang, target_page)
                    self.wd_item["statements"][PROPS["location"]] = wd_item

    def set_inception(self):
        # TODO
        # This is messy and not super prioritized...
        return

    def update_wd_item(self):
        self.update_labels()
        self.set_descriptions()
        self.set_raa()
        self.set_adm_location()
        self.set_type()
        self.set_location()
        self.set_inception()

    def __init__(self, db_row_dict, mapping, data_files):
        Monument.__init__(self, db_row_dict, mapping, data_files)
        self.update_wd_item()


class SeArbetslSv(Monument):

    def update_labels(self):
        return

    def set_descriptions(self):
        DESC_BASE = "arbetslivsmuseum"
        if len(self.typ) > 0:
            self.wd_item["descriptions"] = {self.lang: self.typ.lower()}
        else:
            self.wd_item["descriptions"] = {self.lang: DESC_BASE}

    def add_location_to_desc(self, municipality):
        self.wd_item["descriptions"][self.lang] += " i " + municipality

    def set_adm_location(self):
        municip_dict = self.data_files["municipalities"]
        pattern = self.adm2.lower() + " municipality"
        try:
            municipality = [x["item"] for x in municip_dict if x[
                "en"].lower() == pattern][0]
            ## TODO: Check if target item is valid municipality ##
            self.wd_item["statements"][
                PROPS["located_adm"]] = helpers.listify(municipality)
            swedish_name = [x["sv"]
                            for x in municip_dict
                            if x["item"] == municipality][0]
            self.add_location_to_desc(swedish_name)
        except IndexError:
            print("Could not parse municipality: {}.".format(self.adm2))
            return

    def set_type(self):
        if self.typ:
            table = self.data_files["types"]["mappings"]
            type_to_search_for = self.typ.lower()
            try:
                special_type = [table[x]["items"]
                                for x in table
                                if x.lower() == type_to_search_for][0]
                self.wd_item["statements"]["P31"] = special_type
            except IndexError:
                return
        return

    def set_location(self):
        """
        Items in this table have both ort and address.
        Address is sometimes a valid street address like Värdshusgatan 8
        Ort is usually not wikilinked.
        It can be an urban area or småort and possibly something else...
        In any case, it's a subtype of 'human settlement' in Sweden.
        There are about 12 000 of these, and querying it live would be slow.
        Maybe just download all of them?
        """
        settlements_dict = self.data_files["settlements"]
        if self.ort:
            try:
                location = [x["item"] for x in settlements_dict if x[
                    "sv"].strip() == self.remove_markup(self.ort)][0]
                self.wd_item["statements"][
                    PROPS["location"]] = helpers.listify(location)
            except IndexError:
                print("Could not find ort: " + self.ort)
                return

    def update_wd_item(self):
        self.update_labels()
        self.set_descriptions()
        self.set_adm_location()
        self.set_type()
        self.set_location()

    def __init__(self, db_row_dict, mapping, data_files=None):
        Monument.__init__(self, db_row_dict, mapping, data_files)
        self.update_wd_item()
