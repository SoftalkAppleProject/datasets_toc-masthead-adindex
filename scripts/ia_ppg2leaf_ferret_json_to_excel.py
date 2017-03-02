# -*- coding: utf-8 -*-
"""
    Convert the ia_ppg2leaf_ferret's interim json metadata files to an Excel file.
    -: Jim Salmons :- for FactMiners and The Softalk Apple Project.

"""

import internetarchive
import sys
import json
import pandas as pd

collectionID = ""
source_dir = ""
if len(sys.argv) != 3:
    print("Please supply a command-line argument for the IA collection URL and" +
          " the source directory and try again.")
    exit()
else:
    collectionID = sys.argv[1]
    source_dir = sys.argv[2]


def json_to_excel(item_id):
    global source_dir
    myFile = open(source_dir + '/' + item_id + '_metadata_in_process.json', 'r')
    myObject = myFile.read()
    myFile.close()
    myData = json.loads(myObject)
    #print(myData)
    myFrame = pd.DataFrame(myData)
    dataframes.append(myFrame.T)


found_items = internetarchive.search_items('(collection:' + collectionID + ')')
dataframes = []

print("Rounding up issues...")
for result in found_items:
    issueID = result['identifier']
    print('Processing ' + issueID)
    json_to_excel(issueID)

ppg2leaf_mapFrame = pd.concat(dataframes)
writer = pd.ExcelWriter(source_dir + '/' + collectionID + '_ppg2leaf_map.xlsx')
ppg2leaf_mapFrame.to_excel(writer, collectionID + ' ppg2leaf map')
writer.save()
print("That's all folks!")
