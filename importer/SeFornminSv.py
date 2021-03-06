from Monument import Monument, Dataset
import importer_utils as utils
import importer as importer


class SeFornminSv(Monument):

    def __init__(self, db_row_dict, mapping, data_files, existing, repository):
        super(SeFornminSv, self).__init__(
            db_row_dict, mapping, data_files, existing, repository)
        self.set_monuments_all_id()
        self.set_changed()
        self.wlm_source = self.create_wlm_source(self.monuments_all_id)
        self.set_country()
        self.set_is()
        self.set_heritage()
        self.set_source()
        self.set_registrant_url()
        self.set_image("bild")
        self.update_labels()
        self.set_descriptions()
        self.set_raa()
        self.set_adm_location()
        self.set_type()
        self.set_location()
        self.set_coords(("lat", "lon"))
        self.set_commonscat()
        self.set_wd_item(self.find_matching_wikidata(mapping))

    def update_labels(self):
        """
        Create a label.

        Some of the items have the 'namn' column
        filled out, and others don't.
        If it exists, it looks like:
            [[Grytahögen]]
             Kung Björns Grav
        In which case, use that as a label.
        Otherwise, use the RAÄ number as a label:
            Mellby 84:1
        """
        if len(self.namn) == 0:
            self.add_label("sv", self.raa_nr)
        else:
            self.add_label("sv", utils.remove_markup(self.namn))

    def set_descriptions(self):
        """
        Create a description based on the type and location.

        If the item has a name, which is used for the label,
        add the RAÄ-number to the description in order to make
        sure that the label + description combination is unique.
        When there's no name, the RAÄ-number is used as the label,
        which ensures its uniqueness.
        """
        DESC_BASE = "fornminne"
        landskap = self.landskap
        if len(self.typ) > 0:
            instance_of = self.typ.lower()
        else:
            instance_of = DESC_BASE

        if self.has_non_empty_attribute("namn"):
            description = "{} i {} ({})".format(
                instance_of, landskap, self.raa_nr)
        else:
            description = "{} i {}".format(instance_of, landskap)
        self.add_description("sv", description)

    def set_raa(self):
        """
        Set the "Cultural heritage database in Sweden (P1260)" property.

        All items have a 'raa-nr' and an 'id'.
        The latter is used to link to the
        Database of the cultural heritage in Sweden,
        and the former is used as a qualifier.
        See https://www.wikidata.org/wiki/Property_talk:P1262
        for discussion of rationale.
        """
        fmi_link = "raa/fmi/" + self.id
        raa_qualifier = {"raa-nr": self.raa_nr}
        self.add_statement(
            "cultural_heritage_sweden", fmi_link, raa_qualifier)

    def set_adm_location(self):
        """
        Set the administrative location (municipality).

        Use offline mapping file
        to map municipality to P131.
        The column is 'kommun'.
        It looks like this:
            Alingsås
        Just the name of the municipality
        without the word kommun or genitive.
        """
        municip_dict = self.data_files["municipalities"]
        if self.kommun == "Göteborg":
            municip_name = "Gothenburg"
        else:
            municip_name = self.kommun
        pattern = municip_name.lower() + " municipality"
        try:
            municipality = [x["item"] for x in municip_dict if x[
                "en"].lower() == pattern][0]
            self.add_statement("located_adm", municipality)
        except IndexError:
            print("Could not parse municipality: {}.".format(self.kommun))
            self.add_to_report("kommun", self.kommun)

    def set_type(self):
        """
        Set the P31 property of a certain type of monument.

        All items should have a 'typ', like:
            stensättning
        Use the lookup table from:
        https://www.wikidata.org/wiki/Wikidata:WikiProject_WLM/Mapping_tables/se-fornmin_(sv)/types
        If there's a match, use the more specific
        item as P31.
        Replace the original P31 rather than adding to it.
        """
        if self.has_non_empty_attribute("typ"):
            table = self.data_files["types"]["mappings"]
            type_to_search_for = self.typ.lower()
            try:
                special_type = [table[x]["items"]
                                for x in table
                                if x.lower() == type_to_search_for][0][0]
                self.substitute_statement("is", special_type)
            except IndexError:
                self.add_to_report("typ", self.typ)

    def get_socken(self, socken_name, landskap_name):
        """
        Get the Wikidata ID of a socken.

        Each item has both a 'landskap' and a 'socken'.
        Combine them and get corresponding WD item
        via swedish wikipedia.
        """
        return utils.socken_to_q(socken_name, landskap_name)

    def set_location(self):
        """
        Set location (P276) of object.

        If there's a 'plats' and it's wikilinked use it as location:
            [[Tyresta]]
        It's just a handful of items that have it, though.
        But all should have socken/landskap,
        so use that as location as well.
        """
        if self.has_non_empty_attribute("plats"):
            wikilinks = utils.get_wikilinks(self.plats)
            if len(wikilinks) == 1:
                target_page = wikilinks[0].title
                wd_item = utils.q_from_wikipedia("sv", target_page)
                self.add_statement("location", wd_item)
            else:
                self.add_to_report("plats", self.plats)
        if self.has_non_empty_attribute("socken"):
            socken_dict = self.data_files["socken"]
            socken = self.get_socken(self.socken, self.landskap)
            if socken:
                self.add_statement("location", socken)
            else:
                try:
                    possible_socken = [x["item"] for x in socken_dict
                                       if x["itemLabel"].startswith(self.socken)]
                    if len(possible_socken) != 1:
                        raise ValueError
                    self.add_statement("location", possible_socken[0])
                except (IndexError, ValueError):
                    raw_socken = "{} ({})".format(self.socken, self.landskap)
                    self.add_to_report("socken", raw_socken)

    def set_monuments_all_id(self):
        """Map which column name in specific table to  ID in monuments_all."""
        self.monuments_all_id = self.id

    def exists_with_monument_article(self, language):
        return super().exists_with_monument_article("sv", "artikel")


if __name__ == "__main__":
    """Command line entry point for importer."""
    args = importer.handle_args()
    dataset = Dataset("se-fornmin", "sv", SeFornminSv)
    dataset.data_files = {
        "municipalities": "sweden_municipalities.json",
        "socken": "sweden_socken.json"
    }
    dataset.lookup_downloads = {
        "types": "se-fornmin_(sv)/types"
    }
    importer.main(args, dataset)
