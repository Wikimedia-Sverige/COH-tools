from Monument import Monument
import importer_utils as utils

MAPPING_DIR = "mappings"


class NoNo(Monument):

    def update_descriptions(self):
        """
        Add descriptions in several language.

        In the format "$type in $municipality, ($country if not nb)".
        """
        category = self.kategori.lower()
        municip = self.get_municip_name()
        base_norwegian = "{} i {}"
        desc_norwegian = base_norwegian.format(category, municip)
        self.add_description("nb", desc_norwegian)

        base_english = "cultural property in {}, Norway"
        desc_english = base_english.format(municip)
        self.add_description("en", desc_english)

        base_swedish = "kulturarv i {}, Norge"
        desc_swedish = base_swedish.format(municip)
        self.add_description("sv", desc_swedish)

    def update_labels(self):
        """
        Add label in Bokmål.

        Some of self.navn are in all caps.
        These are normalized:
        FÆRDER FYRSTASJON -> Færder Fyrstasjon
        """
        name = self.navn
        if name.isupper():
            name = name.title()
        self.add_label("nb", name)

    def set_no(self):
        """Add the Norwegian monument ID P758"""
        self.add_statement("norwegian_monument_id", str(self.id))

    def get_municip_name(self):
        """Get the value of self.kommune without brackets."""
        return utils.remove_markup(self.kommune)

    def set_adm_location(self):
        """Set the adm location based on kommunenummer and offline file."""
        all_codes = self.data_files["municipalities"]
        if self.has_non_empty_attribute("kommunenr"):
            municip_code = str(self.kommunenr)
            if len(municip_code) == 3:
                municip_code = "0" + municip_code
            match = [x["item"]
                     for x in all_codes if x["municipNumber"] == municip_code]
            if len(match) == 0:
                self.add_to_report("kommunenr",
                                   municip_code, "located_adm")
            else:
                self.add_statement("located_adm", match[0])

    def set_special_type(self):
        """
        Set special 'is' based on self.kategori and online mapping.

        https://www.wikidata.org/wiki/Wikidata:WikiProject_WLM/Mapping_tables/no_(no)/categories
        """
        glossary = self.data_files["categories"]["mappings"]
        category = self.kategori.lower()
        try:
            special_type = [glossary[x]["items"]
                            for x in glossary
                            if x.lower() == category][0][0]
            self.substitute_statement("is", special_type)
        except IndexError:
            self.add_to_report("kategori", self.kategori, "is")

    def exists_with_monument_article(self, language):
        return super().exists_with_monument_article("no", "monument_article")

    def set_monuments_all_id(self):
        """Map which column name in specific table to  ID in monuments_all."""
        self.monuments_all_id = str(self.id)

    def __init__(self, db_row_dict, mapping, data_files, existing, repository):
        Monument.__init__(self, db_row_dict, mapping,
                          data_files, existing, repository)
        self.set_monuments_all_id()
        self.set_changed()
        self.wlm_source = self.create_wlm_source(self.monuments_all_id)
        self.update_labels()
        self.update_descriptions()
        self.set_special_type()
        self.set_image("bilde")
        self.set_commonscat()
        self.set_coords(("lat", "lon"))
        self.set_no()
        self.set_adm_location()
        self.set_wd_item(self.find_matching_wikidata(mapping))
