import dateparser
from Monument import Monument, Dataset
import importer_utils as utils
import importer as importer


class ThTh(Monument):

    def set_adm_location(self):
        """
        Set the Admin Location.

        First, try the District (amphoe). These are never linked,
        so match against external list.
        If failed, use the Province ISO code matched against external
        list.
        """
        adm_q = None
        prov_dic = self.data_files["provinces"]
        distr_dic = self.data_files["districts"]
        iso = self.prov_iso
        district = self.district

        dist_match = utils.get_item_from_dict_by_key(dict_name=distr_dic,
                                                     search_term=district,
                                                     search_in="itemLabel")
        if len(dist_match) == 1:
            adm_q = dist_match[0]

        if adm_q is None:
            prov_match = utils.get_item_from_dict_by_key(dict_name=prov_dic,
                                                         search_term=iso,
                                                         search_in="iso")
            if len(prov_match) == 1:
                adm_q = prov_match[0]

        if adm_q is not None:
            self.add_statement("located_adm", adm_q)
        else:
            self.add_to_report("district", self.district, "located_adm")

    def set_heritage(self):
        """
        Set heritage status with or without start date.

        If possible to parse the date of when the heritage status was assigned,
        add it as qualifier to the heritage status property.

        Otherwise, add default heritage status without start date.

        `announced` consists of two lines. The date and a reference to the
        issue/volume where it was published.
        """
        if self.has_non_empty_attribute("announced"):
            prot_date = self.announced.split('\n')[0]  # get first row
            d_parsed = dateparser.parse(prot_date)
            if d_parsed:
                date_dict = utils.datetime_object_to_dict(d_parsed)
                date_dict["year"] -= 543  # convert from Thai solar calendar
                qualifier = {"start_time": {"time_value": date_dict}}
                heritage = self.mapping["heritage"]["item"]
                self.add_statement("heritage_status", heritage, qualifier)
            else:
                self.add_to_report("announced", prot_date, "start_time")
                return super().set_heritage()
        else:
            return super().set_heritage()

    def set_heritage_id(self):
        wlm = self.mapping["table_name"].upper()
        self.add_statement("wlm_id", "{}-{}".format(wlm, self.register))

    def update_labels(self):
        th = utils.remove_markup(self.name)
        self.add_label("th", th)

    def update_descriptions(self):
        en = "cultural heritage site in Thailand"
        self.add_description("en", en)

    def set_wd_from_name(self):
        if utils.count_wikilinks(self.name) == 1:
            self.set_wd_item(utils.q_from_first_wikilink("th", self.name))

    def __init__(self, db_row_dict, mapping, data_files, existing, repository):
        Monument.__init__(self, db_row_dict, mapping,
                          data_files, existing, repository)
        self.set_monuments_all_id("register")
        self.set_changed()
        self.set_wlm_source()
        self.set_country()
        self.set_adm_location()
        self.set_is()
        self.set_heritage()
        self.set_heritage_id()
        self.set_commonscat()
        self.set_image()
        self.set_coords()
        self.set_wd_from_name()
        self.update_labels()
        self.update_descriptions()
        self.set_wd_item(self.find_matching_wikidata(mapping))


if __name__ == "__main__":
    """Point of entrance for importer."""
    args = importer.handle_args()
    dataset = Dataset("th", "th", ThTh)
    dataset.data_files = {
        "provinces": "thailand_provinces.json",
        "districts": "thailand_amphoe.json"}
    importer.main(args, dataset)