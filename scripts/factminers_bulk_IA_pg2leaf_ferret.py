#
#  The pg2leaf_ferret examines the Internet Archive's _scandata.xml files to determine
#  the relationship between the scanned document's print page numbers and the sequence
#  numbers assigned to "leaf" images files created during the bulk scanning input process.
#
#  This script is part of the FactMiners and Softalk Apple Project collaboration
#  to develop the Ground Truth edition of the complete 48-issue run of Softalk magazine.
#  The "bulk" processing edition of this script expects a command-line argument that
#  points to a "collection of collections" home/theme page at the Internet Archive.
#
#  For The Softalk Apple Project's interest, we'll run this script on The Computer
#  Magazine Archives (https://archive.org/details/computermagazines).
#

import internetarchive
import os
import re
import csv
import sys
import requests
from lxml import etree

if len(sys.argv) != 3:
    print("Please supply a command-line argument for the IA collection URL and" +
          " the output directory and try again.")
    exit()
else:
    multicollection_url = sys.argv[1]
    output_dir = sys.argv[2]

#
# Step 0. Prep any globals, dev conveniences, etc.
#
no_file_export = False
no_scandata_collections = []
bad_scandata_collections = []
inspected_collections = []
pg2leaf_spec = []
scandata_url = ""

#
# Step 0. Walk through the "collection of collections" page and ferret out the
# pg2leaf relationship for each collection.
#
for filename in os.listdir(output_dir):
    inspected_collections.append(re.sub(r"(?P<inspected_collection>[_\w-]+)_pg2leaf_rpt.csv", r"\g<inspected_collection>",
                                  filename))
collections = internetarchive.search_items('(collection:' + multicollection_url + ')(mediatype:collection)')
for result in collections:
    magazine_collection = result['identifier']
    if magazine_collection not in inspected_collections:
        print(magazine_collection)
        collection = internetarchive.get_item(magazine_collection)
        #
        # Step 1. For each of the collections of computer magazines in the Computer Magazine Archives
        # collection at the Internet Archive...
        #
        issues = internetarchive.search_items('(collection:' + magazine_collection + ')')
        for item in issues:
            issue_id = item['identifier']
            print(issue_id)
            issue = internetarchive.get_item(issue_id)
            #
            # Step 2. For each issue, find get the _scandata.xml file...
            #
            has_scandata = False
            for file in issue.files:
                if '_scandata.xml' in file['name']:
                    print("Found it!", file['name'])
                    has_scandata = True
                    # Process it...
                    # Examine the src_scandata.xml file...
                    scandata_file = issue.get_file(file['name'])
                    scandata = requests.get(scandata_file.url)
                    parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
                    scandata_book = etree.fromstring(scandata.content, parser=parser)
                    # Examine the page elements and gather the leafNums and their respective pgNums...
                    pageData = scandata_book.find('pageData')
                    if pageData is not None:
                        for page in pageData:
                            pageNumber = page.find('pageNumber')
                            if pageNumber is None:
                                pageNumber = "None"
                            else:
                                pageNumber = pageNumber.text
                            pgType = page.find('pageType').text
                            print(page.tag + ' leafNum: ' + page.get('leafNum') + ' pgNum: ' + pageNumber)
                            if pgType != "Color Card":
                                pg2leaf_spec.append([issue_id, page.find('pageType').text, page.get('leafNum'), pageNumber])
                    else:
                        bad_scandata_collections.append(issue_id)
                        has_scandata = False
            print('### Next Issue ###')
            if not has_scandata:
                no_scandata_collections.append(issue_id)
        #
        # Step 3. Generate the Pg2Leaf CSV file for the target collection at the Internet Archive...
        #
        print('##############################')
        print('Generating FactMiners Pg2Leaf Ferret Report :-)')
        if no_file_export:
            print("No files exported.")
        else:
            with open(output_dir + '/' + magazine_collection + '_pg2leaf_rpt.csv', 'w', newline='') as mycsvfile:
                thedatawriter = csv.writer(mycsvfile, dialect='excel')
                # Write the CSV header line at the top of the file...
                thedatawriter.writerow(["Item ID", "PageType", "LeafNum", "PgNum"])
                for row in pg2leaf_spec:
                    thedatawriter.writerow(list(row))
        pg2leaf_spec = []
    else:
        print("Already processed '" + magazine_collection + "'.")
print("THAT'S ALL FOLKS! :-)")
