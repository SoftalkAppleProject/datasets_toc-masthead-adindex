# -*- coding: utf-8 -*-
"""
    Convert the ia_ppg2leaf_ferret's interim json metadata files to an Excel file.
    -: Jim Salmons :- for FactMiners and The Softalk Apple Project.

"""

import internetarchive
import os
import json
import pandas as pd

"""Change the current working directory"""
path = 'C:/Users/salmo/OneDrive/_STAP/IAscanning/pg2leaf_ferret/ia_softalkapple'

if(path == ""):
    path = os.getcwd()

os.chdir(path)
"""End the Working Directory change snippet"""


def json_to_excel(item_id):
    global path
    myFile = open(path + '/' + item_id + '_metadata_in_process.json', 'r')
    myObject = myFile.read()
    myFile.close()
    myData = json.loads(myObject)
    #print(myData)
    myFrame = pd.DataFrame(myData)
    dataframes.append(myFrame.T)


found_items = internetarchive.search_items('(collection:softalkapple)')
dataframes = []

print("Rounding up issues...")
for result in found_items:
    issueID = result['identifier']
    print('Processing ' + issueID)
    json_to_excel(issueID)

ppg2leaf_mapFrame = pd.concat(dataframes)
writer = pd.ExcelWriter(path + '/softalkapple_ppg2leaf_map.xlsx')
ppg2leaf_mapFrame.to_excel(writer, 'Softalk ppg2leaf Map')
writer.save()
print("That's all folks!")
