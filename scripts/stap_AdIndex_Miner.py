#
#  The STAP AdIndex_Miner reads the 48 Advertiser Index dataset files generated for the collection
#  of Softalk Magazines. This data has been gathered from the scans of each issue at the Internet Archive.
#

import os
import re
import csv
import sys

if len(sys.argv) != 3:
    print("Please supply a command-line argument for the source directory " +
          "followed by the output directory and try again.")
    exit()
else:
    source_dir = sys.argv[1]
    output_dir = sys.argv[2]

no_file_export = True

# A unique set of advertisers -- companies, organizations, etc. -- that placed ads
# in one or more issues of Softalk magazine...
advertisers = set()
# Each advertiser has an entry in this collection that has a key of the issue_id and a list of the pages
# on which its ads appeared.
ads_on_pages = []
issueID = set()  # The Issue ID is a concatonation of the Volume and Issue numbers creating a 3 digit ID


###
##
# Utility functions
#
def is_single_page_num(pg_str):
    return re.match(r"[-+]?\d+$", pg_str) is not None


def gather_ads_on_pages(adindex_line: str, volnum: str, issnum: str) -> str:
    # This regex splits the line, ignoring the dotted-line(ish) separator chars and
    # adds the company name and its list of on_page ad placements for the file's issue.
    adindex_line = adindex_line.rstrip()  # remove leading and trailing crap
    if adindex_line:  # skip blank lines
        if adindex_line not in ["ADVERTISER'S INDEX", "ADVERTISERS INDEX", "INDEX OF ADVERTISERS"]:
            company_ads_on_pages = re.sub(
                r"^(?P<company>[\\()'’,\-/& \w]+|[\\()'’,\-/& .\w]+[.][\\()'’,\-/& \w]+)(?:[ ._\-]+)"
                r"\.(?P<on_page>[\d, -]+$|[\d, -]*Cover[\d, -]*|Between[\d, -]*and[\d, \-]*)",
                "\\g<company>\t\\g<on_page>", adindex_line, 0, re.MULTILINE)
            ad_fact = re.split(r'\t+', company_ads_on_pages)
            advertiser = ad_fact[0].strip()
            advertisers.add(advertiser)
            # Next we unpack the pages cited for ads in the issue by this index line..
            page_range = ad_fact[1].strip()
            if "Between" in page_range:
                # This is a singleton condition that happened in the Ad Index due to an advertiser paying
                # for an insert or blow-in card of some sort... we'll have to figure out what this was...
                ads_on_pages.append((advertiser, volnum, issuenum, page_range))
                # print("YIPES! -- " + page_range)
            elif page_range in ["Cover2", "Cover3", "Cover4"]:
                # The entry might be a single-item, non-integer entry...
                # print(page_range)
                ads_on_pages.append((advertiser, volnum, issuenum, page_range))
            elif is_single_page_num(page_range) and int(page_range) < 500:
                # The entry is a basic single page citation...
                # print(page_range)
                ads_on_pages.append((advertiser, volnum, issuenum, page_range))
            else:  # First split again on commas and see if we have a list of page numbers..
                page_range = [x.strip() for x in page_range.split(',')]
                for page in page_range:
                    if "-" in page:
                        # Blow out the individual pages in a dashed page-range...
                        page_range_anchors = [x.strip() for x in page.split('-')]
                        # Handle the special case of a two-page spread on inside front cover
                        if page_range_anchors[0] == "Cover2":
                            start_page = "Cover2"
                            end_page = "1"
                            ads_on_pages.append((advertiser, volnum, issuenum, start_page))
                            ads_on_pages.append((advertiser, volnum, issuenum, end_page))
                        else:
                            start_page = int(page_range_anchors[0])
                            end_page = int(page_range_anchors[1])
                            if end_page - start_page == 1:
                                # It is most likely a two-page spread of facing pages
                                # NOTE: We'll have to check even-odd leaf mappings to programmatically
                                # determine if this is a facing page spread or just two consecutive backing pages
                                ads_on_pages.append((advertiser, volnum, issuenum, str(start_page)))
                                ads_on_pages.append((advertiser, volnum, issuenum, str(end_page)))
                            else:
                                # Otherwise we have a multi-page sequence for which we need a page-wise
                                # dataset of one record per page...
                                for page in list(range(start_page, end_page)):
                                    ads_on_pages.append((advertiser, volnum, issuenum, str(page)))
                                    # print(page_range[0] + ":" + page_range[1])
                    else:
                        # It's a single page reference, so add it to the citations...
                        ads_on_pages.append((advertiser, volnum, issuenum, page))
    return "Ok"


for ad_index_filename in os.listdir(source_dir):
    # A 1-field line signals the start of a subsection where the next X lines are indented
    # with a tab before listing the positions and names of folks in that department/role.
    # When the subsequent lines no longer have an empty first or second field, we're out of the subsection.
    in_subsection = ""
    in_subsubsection = ""

    print("===========================")
    print(ad_index_filename)
    issue_spec = re.sub(r"softalkv(?P<volume_num>\d)n(?P<issue_num>\d{2})(?P<month>\w{3})(?P<year>\d{4})_ad_index\.txt",
                        "\\g<volume_num>\t\\g<issue_num>\t\\g<month>\t\\g<year>", ad_index_filename)
    issue_spec = re.split(r'\t+', issue_spec)
    volnum = issue_spec[0]
    issuenum = issue_spec[1]
    issuemonth = issue_spec[2]
    issueyear = issue_spec[3]

    # Read each line in an ad index file, decipher, console print the result and add the company and its
    # ad page range list (may be a 1-item list) to their respective data set and list.
    with open(source_dir + "/" + ad_index_filename, encoding='utf-8-sig', mode='r') as ad_index_file:
        for ad_line in ad_index_file:  # for each line of the file
            gather_ads_on_pages(ad_line, volnum, issuenum)

sorted_companies = sorted(advertisers)
sorted_ad_sightings = sorted(ads_on_pages)
if no_file_export:
    print("No files exported.")
else:
    with open(output_dir + 'adIndex_advertisers.txt', mode='wt', encoding='utf-8') as outfile:
        outfile.write("\n".join(sorted_companies))
    with open(output_dir + 'adIndex_ad_sightings.txt', mode='wt', encoding='utf-8') as outfile:
        outfile.write("\n".join(("\t".join(i) for i in sorted_ad_sightings)))
    # And export the data as CSV file...
    with open(output_dir + 'adIndex_advertisers.csv', 'w', newline='') as mycsvfile:
        thedatawriter = csv.writer(mycsvfile, dialect='excel')
        # Write the CSV header line at the top of the file...
        thedatawriter.writerow(["ADVERTISER"])
        for row in sorted_companies:
            thedatawriter.writerow([row])
    with open(output_dir + 'adIndex_ad_sightings.csv', 'w', newline='') as mycsvfile:
        thedatawriter = csv.writer(mycsvfile, dialect='excel')
        # Write the CSV header line at the top of the file...
        thedatawriter.writerow(["ADVERTISER", "VOL", "NUM", "PG"])
        for row in sorted_ad_sightings:
            thedatawriter.writerow(row)
print("We have mined " + str(len(ads_on_pages)) + " ad citations so far...")
print("That's all folks!")
