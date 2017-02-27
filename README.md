Softalk Magazine: The TOC, Masthead, and Advertiser Index Corpus - Work In Process
==================================================================================

Project: **The Softalk Apple Project**  
URL: **http://www.SoftalkApple.com**  
Internet Archive collection: **https://archive.org/details/softalkapple**

This repository contains the Softalk magazine (Apple edition) Table of Contents
(TOC), Masthead, and Advertisers Index Corpus as a dataset.

**UPDATE (27 Feb 2017)**: We have uploaded the COMPLETE "ppg2leaf" map -- the metadata 
tuples that relate a Softalk issue's printed page to its respective "leaf" ID which
is the unique component in the page's digitized image filename at the Internet Archive.
In the **ppg2leaf_map** subdirectory, there are 48 interim datafiles in JSON format 
together with an Excel spreadsheet with all 9,547 leafs combined and providing a
pivot table with breakout stats on the ratio, issue by issue, for actual (54%) vs. 
inferred (46%) print page numbers. The full ppg2leaf map is also provided in CSV format.

The **images** subdirectory contains the full-resolution individual page images
for each of the 91 pages that contain one or more of the document structures
included in this dataset. The **djvu_text** directory contains both the djvuXML
and djvu text files generated by the Internet Archive during the stock
digitization process. The **magpage** directory -- currently containing
incomplete work-in-process files -- will collect the files in MAGAZINE and PAGE
format as part of the (upper) **\#GroundTruth** edition of the corpus.

The **scripts** directory includes Python scripts used to generate the text and
CSV files for the masthead staff and Ad Index structures within this corpus.
Please note for non-developers, both the staff and ad gathering scripts expect
to be run via the command-line with the source and output directories (in this
order) supplied as arguments. Developers extending these scripts will need to
provide the required command-line parameters as part of their project run/debug
configuration.

A manifest Excel spreadsheet -- and its equivalent in CSV, JSON, and XML formats
-- is provided.

Softalk TOC/Masthead/AdIndex Dataset by The Softalk Apple Project is licensed
under a Creative Commons Attribution-ShareAlike 4.0 International License.

Based on a work by the Citizen Scientists of The Softalk Apple Project
(http://www.SoftalkApple.com).
