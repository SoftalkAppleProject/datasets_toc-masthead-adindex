#
#  The pg2leaf_ferret examines the Internet Archive's _scandata.xml files to determine
#  the relationship between the scanned document's print page numbers and the sequence
#  numbers assigned to "leaf" images files created during the bulk scanning input process.
#
#  This script is part of the FactMiners and Softalk Apple Project collaboration
#  to develop the Ground Truth edition of the complete 48-issue run of Softalk magazine.
#

import re
import csv
import sys
import requests
from lxml import etree, html, cssselect

if len(sys.argv) != 3:
    print("Please supply a command-line argument for the IA collection URL and" +
          " the output directory and try again.")
    exit()
else:
    collection_url = sys.argv[1]
    output_dir = sys.argv[2]

#
# Step 0. Prep any globals, dev conveniences, etc.
#
no_file_export = False

pg2leaf_spec = []

#
# Step 1. From the Collection homepage, get a sorted list of all items in the
# Softline magazine collection at the Internet Archive...
#
content = requests.get(collection_url)
dochtml = html.fromstring(content.text, base_url=collection_url)
dochtml.make_links_absolute()
# Get the data-id for path building...
select = cssselect.CSSSelector(".item-ia")
rootnames = [el.get('data-id') for el in select(dochtml)]
rootnames = sorted(iter(rootnames))
print(len(rootnames))
# Get the url for each issue...
select = cssselect.CSSSelector(".item-ia .item-ttl a")
issues = [el.get('href') for el in select(dochtml)]
issues = sorted(iter(issues))
for index, issueURL in enumerate(issues):
    if rootnames[index + 1] != "__mobile_header__":
        print(index, issueURL, rootnames[index + 1])
        #
        # Step 2. For each issue, find get the _scandata.xml file...
        #
        rootname = rootnames[index+1]
        # issue_spec = re.sub(r"softalkv(?P<volume_num>\d)n(?P<issue_num>\d{2})(?P<month>\w{3})(?P<year>\d{4})",
        #                     '\\g<volume_num>\t\\g<issue_num>\t\\g<month>\t\\g<year>', rootname)
        # issue_spec = re.split(r'\t', issue_spec)
        scandata_url = "https://archive.org/download/" + rootname + "/" + rootname + "_scandata.xml"

        # Examine the src_scandata.xml file...
        scandata = requests.get(scandata_url)
        scandata_book = etree.fromstring(scandata._content)

        # Examine the page elements and gather the leafNums and their respective pgNums...
        # TODO - New code to gather the computed page numbers, leaf numbers, and gaps...
        pageData = scandata_book.find('pageData')
        for page in pageData:
            pageNumber = page.find('pageNumber')
            if pageNumber is None:
                pageNumber = "None"
            else:
                pageNumber = pageNumber.text
            pgType = page.find('pageType').text
            print(page.tag + ' leafNum: ' + page.get('leafNum') + ' pgNum: ' + pageNumber)
            if pgType != "Color Card":
                # The Softline collection at the Internet Archive is an aggregation of full, partial, and
                # international editions of the magazine, This collection is not then easily parsed with the
                # volume, number, month, year naming convention of the source script provided by the
                # FactMiners and the Softalk Apple Project...
                # pg2leaf_spec.append([issue_spec[0], issue_spec[1], issue_spec[2], issue_spec[3],
                # page.find('pageType').text, page.get('leafNum'),  pageNumber])
                pg2leaf_spec.append([rootname, page.find('pageType').text, page.get('leafNum'),  pageNumber])
        print('### Next Issue ###')
#
# Step 3. Generate the Pg2Leaf CSV file for the Softline collection at the Internet Archive...
#
print('##############################')
print('Generating FactMiners Pg2Leaf Ferret Report :-)')

if no_file_export:
    print("No files exported.")
else:
    with open(output_dir + '/softline_pg2leaf_all.csv', 'w', newline='') as mycsvfile:
        thedatawriter = csv.writer(mycsvfile, dialect='excel')
        # Write the CSV header line at the top of the file...
        thedatawriter.writerow(["Item ID", "PageType", "LeafNum", "PgNum"])
        for row in pg2leaf_spec:
            thedatawriter.writerow(list(row))
print("THAT'S ALL FOLKS! :-)")
