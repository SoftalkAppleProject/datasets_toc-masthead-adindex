# -*- coding: utf-8 -*-
"""
    Convert the ia_ppg2leaf_ferret's interim json metadata files to an XML file.
    This will initially be a simple XML version of the ppg2leaf map via conversion
    of the in-memory Pandas DataFrame.
    -: Jim Salmons :- for FactMiners and The Softalk Apple Project.

"""

import internetarchive
import os
import json
import pandas as pd
from collections import OrderedDict

"""Change the current working directory"""
path = 'C:/Users/salmo/OneDrive/_STAP/IAscanning/pg2leaf_ferret/ia_softalkapple'

if path == "":
    path = os.getcwd()

os.chdir(path)
"""End the Working Directory change snippet"""

xml_header = '<?xml version="1.0" encoding="UTF-8"?>\n\
<MagazineGTS xmlns="http://www.factminers.org/MAGAZINE/gts//2017-02-14"\n\
\txmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n\
\txsi:schemaLocation="http://www.factminers.org/MAGAZINE/gts/2017-02-14/factminers_magazine_gts_schema.xsd"\n\
\tMagazineGTS_Id="{0}">\n\
\t<Metadata>\n\
\t\t<Creator>FactMiners and The Softalk Apple Project</Creator>\n\
\t\t<Created>2017-02-14T12:00:00</Created>\n\
\t\t<LastChange>2017-02-14T12:00:00</LastChange>\n\
\t\t<Comments>{0} issue MAGAZINE Ground Truth Storage</Comments>\n\
\t</Metadata>'


def to_xml(df, item_id=None, mode='w'):
    global path, xml_header

    def df_dict_to_xml(dataframe):
        ordered_fields = OrderedDict([
            (1, 'pageNum'),
            (2, 'ocr_ppg'),
            (3, 'validation'),
            (4, 'pgType'),
            (5, 'handSide'),
            (6, 'issue_id'),
            (7, 'validated_on'),
            (8, 'validator')])
        df_as_dict = dataframe.to_dict()
        xml = [xml_header.format(item_id), '\t<ppg2leaf_map>']
        for leafnum in sorted(df_as_dict.keys(), key=int):
            xml.append('\t\t<leaf leafnum="{0}">'.format(leafnum))
            for field in ordered_fields.values():
                if field == 'validator':
                    xml.append('\t\t\t<{0}>Jim Salmons and Timlynn Babitsky</{0}>'.format(field))
                else:
                    xml.append('\t\t\t<{0}>{1}</{0}>'.format(field, df_as_dict[leafnum][field]))
            xml.append('\t\t</leaf>')
        xml.append('\t</ppg2leaf_map>')
        xml.append('</MagazineGTS>')
        return '\n'.join(xml)
    res = df_dict_to_xml(df)

    if item_id is None:
        return res
    with open(path + '/xml/' + item_id + '_magazine.xml', mode) as f:
        f.write(res)

pd.DataFrame.to_xml = to_xml


def json_to_xml(item_id):
    global path
    myFile = open(path + '/' + item_id + '_metadata_in_process.json', 'r')
    myObject = myFile.read()
    myFile.close()
    myData = json.loads(myObject)
    myFrame = pd.DataFrame(myData)
    myFrame.to_xml(item_id)
    print('Next...')

found_items = internetarchive.search_items('(collection:softalkapple)')
# dataframes = []

print("Rounding up issues...")
for result in found_items:
    issueID = result['identifier']
    print('Processing ' + issueID)
    json_to_xml(issueID)

print("That's all folks!")
