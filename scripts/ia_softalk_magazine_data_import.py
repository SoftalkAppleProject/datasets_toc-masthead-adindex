# -*- coding: utf-8 -*-
"""
    Convert various human-curated #GroundTruth text, CSV, and JSON files to
    FactMiners' MAGAZINE #GTS XML-based metadata output files.
    This will initially be a simple XML version of the ppg2leaf map via conversion
    of the in-memory Pandas DataFrame the output is an early version of
    FactMiners' MAGAZINE #GTS (Ground Truth Storage) metadata file format.
    Update: I am generalizing this script as a housekeeping utility for getting
    mostly one-off datasets created by "pre-ferret" MAGAZINE #GTS compliant
    tools and frameworks, etc.
        -: Jim Salmons :- for FactMiners and The Softalk Apple Project.
"""

import internetarchive
import sys
import json
import pandas as pd
from collections import OrderedDict
import csv
from xml.sax.saxutils import escape

collectionID = ""
source_dir = ""
if len(sys.argv) != 3:
    print("Please supply a command-line argument for the IA collection URL," +
          " and the source directory, then try again.")
    exit()
else:
    collectionID = sys.argv[1]
    source_dir = sys.argv[2]

    current_task = 'adindex2xml'

# This minimal XML header was used in the earliest stages of evolving both
# the MAGAZINE #GTS schema and associated files as well as this script.
# TODO: Among the first things to weed out as the 'ferreting' tools/frameworks evolve
xml_header = '<?xml version="1.0" encoding="UTF-8"?>\n\
<MagazineGTS xmlns="http://www.factminers.org/MAGAZINE/gts/2017-02-14"\n\
\txmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n\
\txsi:schemaLocation="http://www.factminers.org/MAGAZINE/gts/2017-02-14 http://www.factminers.org/MAGAZINE/gts/2017-02-14/factminers_magazine_gts_schema.xsd"\n\
\tMagazineGTS_Id="{0}">\n\
\t<Metadata>\n\
\t\t<Creator>FactMiners and The Softalk Apple Project</Creator>\n\
\t\t<Created>2017-02-14T12:00:00</Created>\n\
\t\t<LastChange>2017-02-14T12:00:00</LastChange>\n\
\t\t<Comments>{0} issue MAGAZINE Ground Truth Storage</Comments>\n\
\t</Metadata>'

#
# Utility functions
#


def get_issue_matrix():
    global source_dir

    # Populate and return the issue_decoder so we can map adindex rows to issueIDs
    matrix_file = source_dir + "/softalk_issue_matrix.csv"
    issue_decoder = OrderedDict()
    issue_decoder[1] = {}
    issue_decoder[2] = {}
    issue_decoder[3] = {}
    issue_decoder[4] = {}
    with open(matrix_file, newline='', encoding='utf-8') as csvfile:
        matrix_data = csv.reader(csvfile, delimiter=',', quotechar='|')
        for row in matrix_data:
            # skip the header row...
            if 'Vol' in row[0]:
                continue
            # Otherwise build up the issue decoding matrix
            issue_decoder[int(row[0])].update({int(row[1]): row[4]})
    # print('Got the issue matrix!')
    return issue_decoder

def to_xml(df, item_id=None, mode='w'):
    global source_dir, xml_header
    # xml_template = open(xml_template, 'r').read()

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
        # xml = [xml_header.format(item_id), '\t<ppg2leaf_map>']
        xml = []
        for leafnum in sorted(df_as_dict.keys(), key=int):
            xml.append('\t\t\t\t<leaf leafnum="{0}">'.format(leafnum))
            for field in ordered_fields.values():
                if field == 'validator':
                    xml.append('\t\t\t\t\t<{0}>Jim Salmons and Timlynn Babitsky</{0}>'.format(field))
                else:
                    xml.append('\t\t\t\t\t<{0}>{1}</{0}>'.format(field, df_as_dict[leafnum][field]))
            xml.append('\t\t\t\t</leaf>')
        # xml.append('\t</ppg2leaf_map>')
        # xml.append('</MagazineGTS>')
        # return '\n'.join(xml)
        return xml_template.format(item_id, '\n'.join(xml))

    res = df_dict_to_xml(df)

    if item_id is None:
        return res
    with open(source_dir + '/xml/' + item_id + '_magazine.xml', mode) as f:
        f.write(res)

# Overshadow the DataFrame to_xml function with our own,
# or create it if not yet available... (TODO: I am fuzzy how to say this)
pd.DataFrame.to_xml = to_xml


def json_to_xml(item_id):
    global source_dir
    myFile = open(source_dir + '/' + item_id + '_metadata_in_process.json', 'r')
    myObject = myFile.read()
    myFile.close()
    myData = json.loads(myObject)
    myFrame = pd.DataFrame(myData)
    myFrame.to_xml(item_id)
    print('Next...')


def adindex_to_xml():
    global source_dir, xml_template
    #item template for {0}
    itemID = ''

    # tab depth
    tabdepth = '\t\t\t\t\t'

    #item template for {1}
    ad_index_listing_template = tabdepth + '<AdIndexListing>{0}\n' + \
        tabdepth + '\t<Issue_id>{1}</Issue_id>\n' + \
        tabdepth + '\t<PageNum>{2}</PageNum>\n' + \
        tabdepth + '</AdIndexListing>\n'

    # 3-piece item template for {2}
    advertiser_entry_open = tabdepth + '<Organization type="company">{0}\n'
    advertiser_entry_altname = tabdepth + '\t<AltName>{0}</AltName>\n'
    advertiser_entry_close = tabdepth + '\t<Profile/>\n' + \
        tabdepth + '\t<Roles>\n' + \
        tabdepth + '\t\t<Role>Advertiser</Role>\n' + \
        tabdepth + '\t</Roles>\n' + \
        tabdepth + '</Organization>\n'

    issue_decoder = get_issue_matrix()

    # Step 1. Read the ad_sightings data and push through item template
    adindex_file = source_dir + "/adIndex_ad_sightings.csv"
    ad_index_listing_xml = u""
    with open(adindex_file, newline='') as csvfile:
        adindex_data = csv.reader(csvfile, delimiter=',')
        for row in adindex_data:
            print(row)
            # skip the header row...
            if 'VOL' in row[1]:
                continue
            advertiser = row[0]
            vol = int(row[1])
            num = int(row[2])
            # Usually an int but sometimes named pg e.g. 'Cover2'
            if row[3].isdigit():
                pg = int(row[3])
            else:
                pg = row[3]
            issueID = issue_decoder[vol][num]
            ad_index_listing_xml += ad_index_listing_template.format(advertiser, issueID, pg)

    # Step 2. Write the dataset of Organizations with the role Advertiser, assume type
    #  is 'company' TBD.
    advertiser_file = source_dir + "/adIndex_advertisers_with_aka.txt"
    advertising_orgs_xml = u""
    with open(advertiser_file, 'r') as txtfile:
        advertiser_data = txtfile.readlines()
        for index, line in enumerate(advertiser_data):
            # skip comment lines...
            if line[0] == '#':
                continue
            # Each line is an org/company to be assigned the Advertiser role.
            if line[0] != '\t':
                # This is the best name for an Advertiser
                # print(line.strip() + ' is an Advertiser')
                advertising_orgs_xml += advertiser_entry_open.format(escape(line.strip()))
                if index < len(advertiser_data) - 1 and \
                        advertiser_data[index + 1][0] != '\t':
                    # print('  End org.')
                    advertising_orgs_xml += advertiser_entry_close
                elif index == len(advertiser_data) - 1:
                    advertising_orgs_xml += advertiser_entry_close
            else:
                # print('  ' + line.strip() + ' is an altName.')
                advertising_orgs_xml += advertiser_entry_altname.format(line.strip())
                if index < len(advertiser_data) - 1 and \
                        advertiser_data[index + 1][0] != '\t':
                    # print('  End Org.')
                    advertising_orgs_xml += advertiser_entry_close
                elif index == len(advertiser_data) - 1:
                    advertising_orgs_xml += advertiser_entry_close

    # Step 3. Pump our xml datasets into their respective positions
    # in the MAGAZINE #GTS publication-level template.
    # print(ad_index_listing_xml)
    # print(advertising_orgs_xml)
    xml_template = open(xml_template, 'r').read()
    publication_xml = xml_template.format(collectionID, ad_index_listing_xml, advertising_orgs_xml)
    # TODO: Shenanigans! I cannot figure out how to get ampersand characters correctly encoded into the output!?
    publication_xml = publication_xml.replace('&', '&amp;')
    with open(source_dir + '/' + collectionID + '_publication.xml', 'w', encoding='utf-8') as f:
        f.write(publication_xml)

    return "Dun did the Ad Index stuff! :-)"


if current_task == 'json_ppg2leaf_2xml':
    xml_template = "TBD"
    found_items = internetarchive.search_items('(collection:softalkapple)')
    print("Rounding up issues and deciding what to do with them...")
    for result in found_items:
        issueID = result['identifier']
        print('Processing ' + issueID)
        json_to_xml(issueID)
elif current_task =='adindex2xml':
    xml_template = source_dir + '/softalkapple_publication_template.xml'
    print('Processing the Ad Index...')
    result = adindex_to_xml()
    print(result)

print("That's all folks!")
