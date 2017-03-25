#
# Some FactMiners ppg2leaf_ferret work-in-process...
#

import internetarchive
import os
import sys
import re
import csv

if len(sys.argv) != 3:
    print("Please supply a command-line argument for the input and output directories" +
          " and try again.")
    exit()
else:
    csv_collection_data_dir = sys.argv[1]
    output_dir = sys.argv[2]

#
# Step 0. Prep any globals, dev conveniences, etc.
#
no_file_export = False
total_computermagazines_collections = 0
total_computermagazines_issues = 0
total_computermagazines_pages = 0
found_pgnums = []

#
# Step 1.
#
for filename in os.listdir(csv_collection_data_dir):
    total_computermagazines_collections += 1
    magazine_collection = re.sub(r"(?P<inspected_collection>[_\w-]+)_pg2leaf_rpt.csv",
                                 r"\g<inspected_collection>", filename)
    issues = set()
    # Read each line in a _scandata.xml report file
    with open(csv_collection_data_dir + "/" + filename, encoding='utf-8-sig', mode='r') as data_file:
        issue_data = data_file.readlines()
        issue_pages = len(issue_data) - 1
        total_computermagazines_pages += issue_pages
        for row in issue_data:
            row = row.strip()
            page_spec = row.split(',')
            if page_spec[0] != 'Item ID':
                issues.add(page_spec[0])
                if page_spec[3] != 'None':
                    page_spec.insert(0, magazine_collection)
                    found_pgnums.append(page_spec)
        total_computermagazines_issues += len(issues)
        print(magazine_collection + " has " + str(len(issue_data) - 1) + " pages in " + str(len(issues)) + " issues.")
#
# Write the CSV datafiles.
# TODO: Write XML-based MAGAZINE GTS format metadata files rather than CSV.
#
print('##############################')
print('Generating FactMiners Pg2Leaf Ferret Output files... :-)')
if no_file_export:
    print("No files exported.")
else:
    with open(output_dir + '/computermagazines_found_pgnum_rpt.csv', 'w', newline='') as mycsvfile:
        thedatawriter = csv.writer(mycsvfile, dialect='excel')
        # Write the CSV header line at the top of the file...
        thedatawriter.writerow(["Collection", "Issue", "PageType", "LeafNum", "PgNum"])
        for row in found_pgnums:
            thedatawriter.writerow(list(row))
print("That's all folks!\nWe have " + str(total_computermagazines_pages) +
      " total pages in " + str(total_computermagazines_issues) + " issues within " + str(total_computermagazines_collections) + " collections of the Computer Magazine Archives ppg2leaf dataset! :-)")
