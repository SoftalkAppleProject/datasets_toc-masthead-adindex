#
#  The STAP StaffMiner reads the 48 staff_only dataset files generated for the collection
#  of Softalk Magazines. This data has been gathered from the scans of the masthead of each issue.
#

import os
import re
import csv
import sys

if len(sys.argv) != 3:
    print("Please supply a command-line argument for the source and output directories and try again.")
    exit()
else:
    source_dir = sys.argv[1]
    output_dir = sys.argv[2]

no_file_export = True

persons = set()
positions = set()
companies = set()
subsections = set()
subsubsections = set()
issueID = set()  # The Issue ID is a concatonation of the Volume and Issue numbers creating a 3 digit ID
# Monthly assignments relate Persons to Positions within Issues
monthly_assignments = []

# NOTE: Currently hardcoded for author's workspace

###
##
# Utility functions
#
def gather_staffing_facts(who: str, didwhat: str, volume_num: str, issue_num: str, subsection: str = "", subsubsection: str = "") -> str:
    # There may be more than one person listed as holding this position for this issue...
    named_persons = re.split(r', ', who)
    # Add the person and position to their respective cumulative sets...
    positions.add(didwhat)
    if subsection:
        subsections.add(subsection)
    if subsubsection:
        subsubsections.add(subsubsection)
    issueID.add(volume_num + issue_num)
    # This only relates to display verbiage, not part of data gathering...
    section_phrase = ""
    if subsection:
        section_phrase = " in " + subsection
    if subsubsection:
        section_phrase = " in " + subsubsection + section_phrase
    for person in named_persons:
        # If the name is wrapped in bracket characters, it is a company and not a person...
        if re.search(r"\[[ ./\w]*\]", person):
            company = re.sub(r"\[(?P<company_name>[ ./\w]*)\]", r"\g<company_name>", person)
            companies.add(company)
        else:
            persons.add(person)
        # If subsection or subsubsection are False, pass an empty string rather than the boolean...
        monthly_assignments.append(
            person + "\t" + didwhat + "\t" + volume_num + "\t" + issue_num + "\t" + subsection + "\t" + subsubsection
        )
        print(person + " was " + didwhat + section_phrase + " for Softalk Vol:" + volume_num + " N:" + issue_num + ".")
    return "Ok"

for staffing_file_name in os.listdir(source_dir):
    # A 1-field line signals the start of a subsection where the next X lines are indented
    # with a tab before listing the positions and names of folks in that department/role.
    # When the subsequent lines no longer have an empty first or second field, we're out of the subsection.
    in_subsection = ""
    in_subsubsection = ""

    print("===========================")
    print(staffing_file_name)
    issue_spec = re.sub(r"softalkv(?P<volume_num>\d)n(?P<issue_num>\d{2})(?P<month>\w{3})(?P<year>\d{4})_staff\.txt",
                        "\\g<volume_num>\t\\g<issue_num>\t\\g<month>\t\\g<year>", staffing_file_name)
    issue_spec = re.split(r'\t+', issue_spec)
    volnum = issue_spec[0]
    issuenum = issue_spec[1]
    issuemonth = issue_spec[2]
    issueyear = issue_spec[3]

    # Read each line in a staffing file and display if it is the basic position/name format
    with open(source_dir + "/" + staffing_file_name, encoding='utf-8-sig', mode='r') as staff_file:
        for line in staff_file:  # for each line of the file
            line = line.rstrip()  # remove leading and trailing crap
            if line:  # skip blank lines
                fact_line = re.sub(r"^(?P<position>[ .\w]+)\t(?P<name>[ .\w]+)", "\\g<position>\t\\g<name>",
                                   line, 0, re.IGNORECASE | re.MULTILINE)
                staffing_fact = re.split(r'\t+', fact_line)
                # The most standard and early entries are tab-delimited, two-field
                # with POSITION and NAME data. Files begin with these column headers which should be ignored.
                if staffing_fact[0] != "POSITION":
                    # One-field lines are subsection labels for dept/category
                    if len(staffing_fact) == 1:
                        in_subsection = staffing_fact[0]
                        print("------------")
                        print(staffing_fact[0])
                    else:
                        # If the line is not a basic position/name entry, it is either a dept/category
                        # label for a subsection or it is a position/name entry within a dept/category.
                        if (len(staffing_fact) == 2) and (staffing_fact[0] == ""):
                            # In this case, the line starts with two tabs and is a subsubsection label...
                            in_subsubsection = staffing_fact[1]
                            print("------------")
                            print(staffing_fact[1])
                        elif (in_subsection is not "") and (in_subsubsection is not ""):
                            # This handles subsubsection position/name lines...
                            gather_staffing_facts(staffing_fact[2], staffing_fact[1], volnum, issuenum, in_subsection, in_subsubsection)
                        elif (in_subsection is not "") and (staffing_fact[0] == ""):
                            # This handles subsection position/name entries...
                            gather_staffing_facts(staffing_fact[2], staffing_fact[1], volnum, issuenum, in_subsection)
                            in_subsubsection = ""
                        else:
                            # If no other condition is met, the line is a basic position/name entry...
                            gather_staffing_facts(staffing_fact[1], staffing_fact[0], volnum, issuenum, in_subsection, in_subsubsection)
                            in_subsection = ""
                            in_subsubsection = ""
if no_file_export:
    print("No files exported.")
else:
    # Write a sorted list, in text & CSV formats, of people who worked at Softalk (per the masthead)...
    sorted_persons = sorted(persons)
    with open(output_dir + 'staff_persons.txt', mode='wt', encoding='utf-8') as outfile:
        outfile.write("\n".join(sorted_persons))
    # And export the data as CSV file...
    with open(output_dir + 'staff_persons.csv', 'w', newline='') as mycsvfile:
        thedatawriter = csv.writer(mycsvfile, dialect='excel')
        # Write the CSV header line at the top of the file...
        thedatawriter.writerow(["PERSON"])
        for row in sorted_persons:
            thedatawriter.writerow([row])
    # Write a sorted list, in text & CSV formats, of contractor companies for Softalk (per the masthead)...
    sorted_companies = sorted(companies)
    with open(output_dir + 'staff_companies.txt', mode='wt', encoding='utf-8') as outfile:
        outfile.write("\n".join(sorted_companies))
    # And export the data as CSV file...
    with open(output_dir + 'staff_companies.csv', 'w', newline='') as mycsvfile:
        thedatawriter = csv.writer(mycsvfile, dialect='excel')
        # Write the CSV header line at the top of the file...
        thedatawriter.writerow(["COMPANY"])
        for row in sorted_companies:
            thedatawriter.writerow([row])
    # Write a sorted list, in text & CSV formats, of named positions of folks who worked at Softalk...
    sorted_positions = sorted(positions)
    with open(output_dir + 'staff_positions.txt', mode='wt', encoding='utf-8') as outfile:
        outfile.write("\n".join(sorted_positions))
    # And export the data as CSV file...
    with open(output_dir + 'staff_positions.csv', 'w', newline='') as mycsvfile:
        thedatawriter = csv.writer(mycsvfile, dialect='excel')
        # Write the CSV header line at the top of the file...
        thedatawriter.writerow(["POSITION"])
        for row in sorted_positions:
            thedatawriter.writerow([row])
    # Write a sorted list, in text & CSV formats, of each monthly staff assignment per the masthead...
    sorted_assignments = sorted(monthly_assignments)
    with open(output_dir + 'staff_assignments.txt', mode='wt', encoding='utf-8') as outfile:
        outfile.write("\n".join(sorted_assignments))
    # And export the data as CSV file...
    with open(output_dir + 'staff_assignments.csv', 'w', newline='') as mycsvfile:
        thedatawriter = csv.writer(mycsvfile, dialect='excel')
        # Write the CSV header line at the top of the file...
        thedatawriter.writerow(["PERSON", "POSITION", "VOL", "NUM", "CATEGORY", "SUBCATEGORY"])
        for row in sorted_assignments:
            thedatawriter.writerow(re.split(r'\t', row))
print("That's all folks!")
