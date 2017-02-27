#
# Some FactMiners ppg2leaf_ferret work-in-process...
#

import internetarchive
import os
from threading import Thread
import re
import sys
import requests
from lxml import etree
import wx
from wx import xrc
from wx.lib.pubsub import pub
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
# import io
from PIL import Image
import tesserocr
# from tesserocr import PyTessBaseAPI
from tesserocr import PSM
import json
import time
from collections import OrderedDict

print(tesserocr.tesseract_version())  # print tesseract-ocr version
print(tesserocr.get_languages())  # prints tessdata path and list of available languages

collectionID = ""
output_dir = ""
if len(sys.argv) != 3:
    print("Please supply a command-line argument for the IA collection URL and" +
          " the output directory and try again.")
    exit()
else:
    collectionID = sys.argv[1]
    output_dir = sys.argv[2]

done_issues = []
issues_todo = []

print(collectionID)
# collectionObj = internetarchive.get_item(collectionID)

for filename in os.listdir(output_dir):
    done_issues.append(re.sub(r"(?P<inspected_collection>[_\w-]+)_metadata_in_process.json",
                              r"\g<inspected_collection>", filename))
found_items = internetarchive.search_items('(collection:' + collectionID + ')')
print("Rounding up issues...")
for result in found_items:
    issueID = result['identifier']
    if issueID not in done_issues:
        print(issueID)
        issues_todo.append(issueID)

print("Ready to rumble!!!")


class GetImageThread(Thread):
    """This thread handles getting a leaf image from the Internet Archive
        destined for the pg_queue."""

    def __init__(self, issue_id="", leafnum=0, maxheight=0, handside='', offset=2, zoom_zone='top'):
        """Init the Worker Thread that queues leaf images."""
        Thread.__init__(self)
        self.issue_id = issue_id
        self.current_leaf = leafnum
        self.maxheight = maxheight
        self.handside = handside
        self.zoom_zone = zoom_zone
        # # TODO: A bit of a cheat to help init'ing the queue...
        # if offset < 2:
        #     self.offset = 2
        # else:
        self.offset = offset
        self.corner_offset = 50
        self.daemon = True
        self.start()  # start the thread

    def run(self):
        """Run GetImage Worker Thread to grab an image from the Internet Archive."""
        # print("Getting leaf " + str(self.current_leaf))
        req = Request("https://archive.org/download/" +
                      self.issue_id + "/page/leaf" + str(self.current_leaf))
        try:
            ia_reply = urlopen(req)
        except HTTPError as e:
            print('The server couldn\'t fulfill the request.')
            print('Error code: ', e.code)
        except URLError as e:
            print('We failed to reach a server.')
            print('Reason: ', e.reason)
        else:
            pil_image = Image.open(ia_reply)
            # First, do the full-page image...
            resize_percent = self.maxheight / pil_image.size[1]
            wsize = int((float(pil_image.size[0]) * float(resize_percent)))
            pil_sm_image = pil_image.resize((int(wsize), int(self.maxheight)), Image.BICUBIC)
            image = wx.Image(pil_sm_image.size[0], pil_sm_image.size[1])
            image.SetData(pil_sm_image.convert("RGB").tobytes())
            # then do the cornerzoom image
            img_in_process = pil_image.copy()
            if self.zoom_zone == 'top':
                if self.handside == 'LEFT':
                    cornerzoom_img = img_in_process.crop((self.corner_offset, 1, self.corner_offset + 240, 240))
                else:
                    cornerzoom_img = img_in_process.crop(((img_in_process.width - self.corner_offset - 240), 1,
                                                          img_in_process.width - self.corner_offset, 240))
            else:
                # Print page numbers are on the bottom of the page...
                if self.handside == 'LEFT':
                    cornerzoom_img = img_in_process.crop((1, (img_in_process.height - 240), 240, img_in_process.height))
                else:
                    cornerzoom_img = img_in_process.crop(((img_in_process.width - 240), (img_in_process.height - 240),
                                                          img_in_process.width, img_in_process.height))
            # OCR the zoom image...
            rawline = tesserocr.image_to_text(cornerzoom_img, psm=PSM.RAW_LINE)
            # print('Raw: ' + rawline)
            digit_str = re.sub(r"\D", "", rawline)
            digit_int = self.ppg_sensemaker(digit_str)
            print("OCR ppg2leaf map - " + str(self.current_leaf) + ":" + str(digit_int))
            # TODO: Hard-coded to size of wx.Panel, move to user settings when added.
            cornerzoom_img = cornerzoom_img.resize((110, 110), Image.BICUBIC)
            zoom_img = wx.Image(cornerzoom_img.size[0], cornerzoom_img.size[1])
            zoom_img.SetData(cornerzoom_img.convert("RGB").tobytes())
            wx.CallAfter(lambda *a: pub.sendMessage("image_ready", img=image, zoom_image=zoom_img,
                                                    leaf=self.current_leaf, printed_ppg=digit_int))

    def ppg_sensemaker(self, digit_str):
        # Case 0: If digit_str is None, go with it...
        if digit_str is None or not digit_str:
            return None
        # Case 1: The observed digit_str is equal to the current leafnum
        # minus the documents typical offset.
        elif int(digit_str) == (self.current_leaf - self.offset):
            return int(digit_str)
        # Case 2: Look for the string of the current leaf in digit_str
        elif str(self.current_leaf - self.offset) in digit_str:
            return self.current_leaf - self.offset
        # Case 3: The int value of digit_str is "close" to the expected ppg
        # TODO: A bit of a range cheat...
        # elif int(digit_str) in range(self.current_leaf - self.offset, self.current_leaf + self.offset):
        elif int(digit_str) in range(self.current_leaf - 10, self.current_leaf + 10):
            return int(digit_str)
        else:
            return None


class IaPpg2Leaf_FerretApp(wx.App):

    def OnInit(self):
        self.res = xrc.XmlResource('ia_ppg2leaf_ferret.xrc')
        self.init_frame()
        return True

    def init_frame(self):
        self.frame = self.res.LoadFrame(None, 'ID_APPWIN')
        self.frame_title_root = "FactMiners ppg2leaf Ferret -- Viewing: "
        self.leafpanel = self.getControl('ID_LEAF_PANEL')
        self.zoompanel = self.getControl('ID_CORNERZOOM')
        # Menu items and handler bindings...
        self.nextissuetaskID = self.getControl('ID_NEXT_ISSUE_TASK').Id
        self.frame.Bind(wx.EVT_MENU, self.getnextissue, self.getControl('ID_NEXT_ISSUE_TASK'))
        self.Bind(wx.EVT_MENU, self.getnextissue, None, id=self.nextissuetaskID)
        self.savemaptaskID = self.getControl('ID_SAVE_MAP_TASK').Id
        self.frame.Bind(wx.EVT_MENU, self.save_map, self.getControl('ID_SAVE_MAP_TASK'))
        self.Bind(wx.EVT_MENU, self.save_map, None, id=self.savemaptaskID)
        self.settingstaskID = self.getControl('ID_SETTINGS_TASK').Id
        self.frame.Bind(wx.EVT_MENU, self.settings_dialog, self.getControl('ID_SETTINGS_TASK'))
        self.Bind(wx.EVT_MENU, self.settings_dialog, None, id=self.settingstaskID)
        # UI widgets...
        self.pgtype_widget = self.getControl('ID_PAGETYPE')
        self.leafnum_widget = self.getControl('ID_LEAFNUM')
        self.ppgnum_widget = self.getControl('ID_PPGNUM_NAME')
        self.nextleaf_btn = self.getControl('ID_NEXTLEAF')
        self.prevleaf_btn = self.getControl('ID_PREVLEAF')
        self.rb_group = self.getControl('ID_RBGROUP')
        self.printed_rb = self.getControl('ID_PRINTED_RB')
        self.inferred_rb = self.getControl('ID_INFER_RB')
        self.inferred_checkbox = self.getControl('ID_INFERRED_ONLY')

        self.getpicbut = xrc.XRCCTRL(self.frame, 'ID_NEXTLEAF')
        self.getpicbut.Bind(wx.EVT_BUTTON, self.showleaf)
        self.getprevpicbut = xrc.XRCCTRL(self.frame, 'ID_PREVLEAF')
        self.getprevpicbut.Bind(wx.EVT_BUTTON, self.showleaf)
        self.img = wx.StaticBitmap(self.leafpanel, wx.ID_ANY, wx.Bitmap())
        self.zoomimg = wx.StaticBitmap(self.zoompanel, wx.ID_ANY, wx.Bitmap())
        self.path = None
        self.current_issue = None
        self.no_file_export = True
        self.current_issue_index = -1
        self.queue_max = 0
        self.issue_id = ""
        self.done_issues = done_issues
        self.issues_todo = issues_todo
        self.pg2leaf_spec = OrderedDict()
        # Archive _scandata.xml files have two profile: uploaded 'skinny' & Archive-scanned 'detailed'
        # Our Softalk collection was scanned at the Ft. Wayne Regional Scanning Center so it's not skinny
        self.skinny_scandata = False
        #  TODO: Image height offset is hard-coded and needs dynamic fix or user setting
        self.maxheight = wx.GetDisplaySize().Height - 140
        self.pg_queue = {}
        self.zoom_queue = {}
        self.printed_ppg_queue = {}
        self.gap_pgs = []
        #  TODO: pg_queue hard-coded set to 10, needs user setting
        self.pg_queue_size = 20
        # TODO: Need a _scandata.xml file adjustment based on 'profile'
        # Leaf 0 is the ColorCard, Leaf 1&2 are Cover1&2,
        #  so leaf 3 is ppg 1, offset = 2 to start...
        self.zoom_zone = 'top'
        if self.zoom_zone == 'top':
            self.current_leaf = 1
            # self.ppg2leaf_offset = 2
        else:
            self.current_leaf = 0
            # self.ppg2leaf_offset = 1
        self.printed_rb.Bind(wx.EVT_RADIOBUTTON, self.dehighlight)
        self.inferred_rb.Bind(wx.EVT_RADIOBUTTON, self.dehighlight)
        pub.subscribe(self.queue_updated, 'image_ready')
        self.getnextissue(None)

    def dehighlight(self, event):
        self.rb_group.SetBackgroundColour(wx.NullColour)
        self.rb_group.Refresh()

    def getnextissue(self, event):
        print("Fetchin' next issue...")
        self.current_issue_index += 1
        # TODO: the scandata profile needs to adjust this
        if self.zoom_zone == 'top':
            self.current_leaf = 1
        else:
            self.current_leaf = 0
        self.issue_id = self.issues_todo[self.current_issue_index]
        # self.issue_id = 'byte-magazine-1981-08'
        self.frame.Title = self.frame_title_root + self.issue_id
        print("Ready to work on: " + self.issue_id)
        self.current_issue = internetarchive.get_item(self.issue_id)
        print("Found " + self.current_issue.identifier)
        #  Find the _scandata.xml file and load the ppg2leaf data from PageData...
        self.pg2leaf_spec = {}
        self.getscandata()
        self.pg_queue = {}
        self.zoom_queue = {}
        self.gap_pgs = []
        self.queue_max = 0
        self.ppg2leaf_offset = 0
        self.init_pg_queue()

    def init_pg_queue(self):
        if self.zoom_zone == 'top':
            starting_leaf = 1
        else:
            starting_leaf = 0
        for i in range(starting_leaf, self.pg_queue_size):
            if self.queue_max <= i:
                self.queue_max = i
            GetImageThread(self.issue_id, leafnum=i, maxheight=self.maxheight,
                           handside=self.pg2leaf_spec[i]['handSide'], offset=self.ppg2leaf_offset, zoom_zone=self.zoom_zone)

    def queue_updated(self, leaf, img, zoom_image, printed_ppg):
        self.pg_queue[leaf] = img
        self.zoom_queue[leaf] = zoom_image
        self.printed_ppg_queue[leaf] = printed_ppg
        if self.current_leaf == leaf:
            self.showleaf()
        # print('Page and zoom queue added images for leaf: ', leaf, '.')

    def showleaf(self, event=None):
        if event is not None:
            if event.EventObject.Name == 'ID_NEXTLEAF':
                self.save_spec()
                self.current_leaf += 1
                self.advance_queue()
            elif event.EventObject.Name == 'ID_PREVLEAF':
                self.save_spec()
                self.current_leaf -= 1
                self.retreat_queue()
        self.check_leaf_btns()
        if self.current_leaf not in self.pg2leaf_spec.keys():
            self.current_leaf += 1
            self.showleaf()
        else:
            self.setSpec(self.current_leaf)
            # self.handle_inferred_only()
            self.img.SetBitmap(self.pg_queue[self.current_leaf].ConvertToBitmap())
            self.leafpanel.Refresh()
            self.zoomimg.SetBitmap(self.zoom_queue[self.current_leaf].ConvertToBitmap())
            self.zoompanel.Refresh()
            #  Size the Frame
            imgsize = self.img.Size
            x = imgsize[0] + 170
            y = imgsize[1] + 80
            self.frame.Size = (x, y)
            self.frame.Show()

    def handle_inferred_only(self):
        # If the _scandata.xml assertion of a ppg OR the anticipated ppg (based on the
        # current leaf offset) is the same as the OCRed ppg, don't show it and keep looking.
        # print("Handle inferred only...")
        if self.inferred_checkbox.IsChecked():
            anticipated_ppg = self.current_leaf - self.ppg2leaf_offset
            if int(self.pg2leaf_spec[self.current_leaf]['pageNum']) == anticipated_ppg or self.printed_ppg_queue[self.current_leaf] == anticipated_ppg:
                self.current_leaf += 1
                self.setSpec(self.current_leaf)
                self.advance_queue()
                self.handle_inferred_only()

    def save_spec(self):
        # Before we do anything, check if the offset is changing...
        if self.current_leaf not in self.gap_pgs:
            if self.ppgnum_widget.GetValue() in ['Insert Stub', 'Insert Content', 'Foldout']:
                self.ppg2leaf_offset -= 1
                self.gap_pgs.append(self.current_leaf)
                print('Offset: ' + str(self.ppg2leaf_offset))
            # In rare case of missing pages, compute a new offset....
            if self.pgtype_widget.GetValue() == 'MissingPgs':
                # When the pgType is set to 'MissingPgs', the ppgnum widget's value is
                #   taken as the new ppgnum and the offset is computed based on it...
                current_offset = self.ppg2leaf_offset
                self.ppg2leaf_offset = int(self.ppgnum_widget.GetValue()) - self.current_leaf
                print('Offset ' + str(current_offset) + ' now ' + str(self.ppg2leaf_offset))
                self.gap_pgs.append(self.current_leaf)
        if self.printed_rb.GetValue() is True:
            validation = 'printed'
            # TODO: The user's name will be one of the user settings...
            self.pg2leaf_spec[int(self.current_leaf)]['validator'] = 'Jim Salmons'
            self.pg2leaf_spec[int(self.current_leaf)]['validated_on'] = time.strftime('%x %X %z')
        elif self.inferred_rb.GetValue() is True:
            validation = 'inferred'
            # TODO: The user's name will be one of the user settings...
            self.pg2leaf_spec[int(self.current_leaf)]['validator'] = 'Jim Salmons'
            self.pg2leaf_spec[int(self.current_leaf)]['validated_on'] = time.strftime('%x %X %z')
        else:
            validation = None
        if self.ppgnum_widget.GetValue() == '':
            self.pg2leaf_spec[int(self.current_leaf)]['pageNum'] = \
                self.ppgnum_widget.Strings[self.ppgnum_widget.GetSelection()]
        else:
            self.pg2leaf_spec[int(self.current_leaf)]['pageNum'] = \
                self.ppgnum_widget.GetValue()
        self.pg2leaf_spec[int(self.current_leaf)]['pgType'] = \
            self.pgtype_widget.GetStringSelection()
        self.pg2leaf_spec[int(self.current_leaf)]['validation'] = validation
        self.pg2leaf_spec[int(self.current_leaf)]['ocr_ppg'] = \
            self.printed_ppg_queue[self.current_leaf]

    def getscandata(self):
        for file in self.current_issue.files:
            if '_scandata.xml' in file['name']:
                print("Found it!", file['name'])
                # Process it...
                scandata_file = self.current_issue.get_file(file['name'])
                scandata = requests.get(scandata_file.url)
                parser = etree.XMLParser(ns_clean=True, recover=True, encoding='utf-8')
                scandata_book = etree.fromstring(scandata.content, parser=parser)
                # Examine the page elements and gather the leafNums and their respective pgNums...
                pageData = scandata_book.find('pageData')
                if pageData is not None:
                    for page in pageData:
                        leafNum = page.get('leafNum')
                        pageNumber = page.find('pageNumber')
                        if pageNumber is None:
                            pageNumber = "None"
                        else:
                            pageNumber = pageNumber.text
                        if page.find('handSide') is not None:
                            handSide = page.find('handSide').text
                        else:
                            # Compute handside based on even/odd
                            if bool(int(leafNum) % 2):
                                handSide = 'LEFT'
                            else:
                                handSide = 'RIGHT'
                        pgType = page.find('pageType').text
                        if pgType not in ['Color Card', 'Delete']:
                            print(page.tag + ' leafNum: ' + page.get('leafNum') + ' pgNum: ' + pageNumber)
                            self.pg2leaf_spec[int(leafNum)] = {
                                'issue_id': self.issue_id, 'pgType': pgType, 'pageNum': pageNumber, 'handSide': handSide}

    def getControl(self, xmlid):
        '''Retrieves the given control (within a dialog) by its xmlid'''
        control = self.frame.FindWindowById(xrc.XRCID(xmlid))
        if control is None and self.frame.GetMenuBar() is not None:  # see if on the menubar
            control = self.frame.GetMenuBar().FindItemById(xrc.XRCID(xmlid))
        assert control is not None, 'Programming error: a control with xml id ' + xmlid + ' was not found.'
        return control

    def setSpec(self, leafnum):
        spec = self.pg2leaf_spec[leafnum]
        # TODO: If there is an errant 'Title' pageType (w/o attending to Issuing Rules...),
        if spec['pgType'] == 'Title':
            pgtype_index = self.pgtype_widget.Items.index('Cover')
            # self.ppg2leaf_offset += 1
        else:
            pgtype_index = self.pgtype_widget.Items.index(spec['pgType'])
        self.pgtype_widget.SetSelection(pgtype_index)
        self.leafnum_widget.LabelText = str(leafnum) + ' of ' + str(list(self.pg2leaf_spec.keys())[-1])
        if 'validation' in spec.keys():
            if spec['validation'] == 'printed':
                self.printed_rb.SetValue(True)
            elif spec['validation'] == 'inferred':
                self.inferred_rb.SetValue(True)
            self.rb_group.Refresh()
            # If it's a digit, set the page number text string, otherwise it is a special name
            #   and we find its list selection index number and set it...
            if spec['pageNum'].isdigit():
                self.ppgnum_widget.SetValue(spec['pageNum'])
            else:
                pgnum_index = self.ppgnum_widget.Items.index(spec['pageNum'])
                self.ppgnum_widget.SetSelection(pgnum_index)
            self.ppgnum_widget.SetBackgroundColour(wx.NullColour)
        # The first two leafs are Cover1&2 and last two Cover3&4...
        elif leafnum in [0, 1, 2,
                         list(self.pg2leaf_spec.keys())[-2],
                         list(self.pg2leaf_spec.keys())[-1]]:
            self.ppg2leaf_offset -= 1
            if leafnum == 0 and spec['pgType'] == 'Title':
                self.ppgnum_widget.SetValue('Cover1')
                self.skinny_scandata = True
            elif leafnum == 1 and spec['pgType'] == 'Cover':
                self.ppgnum_widget.SetValue('Cover1')
            elif leafnum == 1:
                self.ppgnum_widget.SetValue('Cover2')
            elif leafnum == 2 and not self.skinny_scandata:
                self.ppgnum_widget.SetValue('Cover2')
            elif leafnum == 2:
                self.ppgnum_widget.SetValue('1')
            # Recognize back covers...
            elif list(self.pg2leaf_spec.keys()).index(leafnum) == (len(self.pg2leaf_spec) - 2):
                self.ppgnum_widget.SetValue('Cover3')
            elif list(self.pg2leaf_spec.keys()).index(leafnum) == (len(self.pg2leaf_spec) -1):
                self.ppgnum_widget.SetValue('Cover4')
            self.ppgnum_widget.SetBackgroundColour(wx.Colour(255, 180, 180))
            self.rb_group.SetBackgroundColour(wx.Colour(255, 180, 180))
            self.inferred_rb.SetFocus()
            self.rb_group.Refresh()
        elif spec['pageNum'] == "None":
            # If we spotted one, put it up w/ background color highlighting...
            if self.printed_ppg_queue[leafnum] is not None:
                self.ppgnum_widget.SetValue(str(self.printed_ppg_queue[leafnum]))
                self.ppgnum_widget.SetBackgroundColour(wx.Colour(255, 180, 180))
                self.printed_rb.SetValue(True)
                self.rb_group.SetBackgroundColour(wx.NullColour)
                self.rb_group.Refresh()
                # self.leafnum_widget.SetFocus()
            else:
                # There is no ppg in the spec nor seen by OCR, so make a good guess...
                self.ppgnum_widget.SetValue(str((leafnum + self.ppg2leaf_offset)))
                self.ppgnum_widget.SetBackgroundColour(wx.Colour(255, 180, 180))
                self.printed_rb.SetValue(False)
                self.inferred_rb.SetValue(False)
                self.rb_group.SetBackgroundColour(wx.Colour(255, 180, 180))
                self.inferred_rb.SetFocus()
                self.rb_group.Refresh()
                # self.leafnum_widget.SetFocus()
        elif spec['pageNum'].isdigit():
            self.ppgnum_widget.SetValue(spec['pageNum'])
            self.ppgnum_widget.SetBackgroundColour(wx.NullColour)
            # TODO: Hmmmm... should not need this check...
            if leafnum in self.printed_ppg_queue.keys() and int(spec['pageNum']) == self.printed_ppg_queue[leafnum]:
            # if int(spec['pageNum']) == self.printed_ppg_queue[leafnum]:
                self.printed_rb.SetValue(True)
                self.rb_group.SetBackgroundColour(wx.NullColour)
            else:
                self.inferred_rb.SetValue(True)
                self.inferred_rb.SetFocus()
                self.rb_group.SetBackgroundColour(wx.Colour(255, 180, 180))
            self.rb_group.Refresh()
            # self.leafnum_widget.SetFocus()
        # If we have an observed ppg, show it and set background color
        elif self.printed_ppg_queue[leafnum] is not None:
            self.ppgnum_widget.SetValue(self.printed_ppg_queue[leafnum])
            self.ppgnum_widget.SetBackgroundColour(wx.Colour(255, 180, 180))
            self.printed_rb.SetValue(True)
            # self.leafnum_widget.SetFocus()
        else:
            # TODO: This should not happen...
            print("Oops... the ppgnum widget has hiccups...")

    def advance_queue(self):
        if self.queue_max != list(self.pg2leaf_spec.keys())[-1]:
            self.queue_max += 1
            # If this leafnum in the _scandata spec? (E.g. due to pgType 'Deleted')
            if self.queue_max - self.current_leaf < self.pg_queue_size:
                print("Accelerating queue caching...")
                zoomside = self.pg2leaf_spec[self.queue_max]['handSide']
                GetImageThread(self.issue_id, leafnum=self.queue_max, maxheight=self.maxheight, handside=zoomside, offset=self.ppg2leaf_offset)
                self.advance_queue()
            elif self.queue_max not in self.pg2leaf_spec.keys():
                # TODO: Hunh?.... Offset computation is a wip...
                print('Offset reduced by one to ' + str(self.ppg2leaf_offset))
                self.ppg2leaf_offset -= 1
                self.advance_queue()
            else:
                zoomside = self.pg2leaf_spec[self.queue_max]['handSide']
                GetImageThread(self.issue_id, leafnum=self.queue_max, maxheight=self.maxheight, handside=zoomside, offset=self.ppg2leaf_offset)
                # print("Queue advanced!")

    def retreat_queue(self):
        # TODO: Eventually we will age out queue items...
        print("Queue retreats!")

    def check_leaf_btns(self):
        if self.current_leaf > 1 and not self.skinny_scandata:
            self.prevleaf_btn.Enable(True)
        elif self.current_leaf > 0 and self.skinny_scandata:
            self.prevleaf_btn.Enable(True)
        else:
            self.prevleaf_btn.Enable(False)
        if self.current_leaf >= list(self.pg2leaf_spec.keys())[-1]:
            self.nextleaf_btn.Enable(False)
        else:
            self.nextleaf_btn.Enable(True)

    def settings_dialog(self, event):
        print("Settings dialog TBD")

    def save_map(self, event):
        print("Writin' this issue....")
        with open(output_dir + '\\' + self.issue_id + '_metadata_in_process.json', 'w') as f:
            json.dump(self.pg2leaf_spec, f, ensure_ascii=False)


if __name__ == '__main__':
    app = IaPpg2Leaf_FerretApp(False)
    app.SetTopWindow(app.frame)
    app.MainLoop()
