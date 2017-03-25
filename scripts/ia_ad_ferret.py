#
# Some FactMiners ad_ferret work-in-process...
#

import internetarchive
from pathlib import Path
from threading import Thread
# import queue
import re
import sys
import wx
from wx import xrc
from wx.lib.pubsub import pub
import wx.lib.buttons as buttons
import xmltodict
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from PIL import Image, ImageDraw, ImageFont
from collections import OrderedDict
import time
# import os
# import io
# import requests
# from lxml import etree
# import json


collectionID = ""
output_dir = ""

if len(sys.argv) != 3:
    print("Please supply a command-line argument for the IA collection URL and" +
          " the output directory and try again.")
    exit()
else:
    collectionID = sys.argv[1]
    output_dir = sys.argv[2]

print(collectionID)
# collectionObj = internetarchive.get_item(collectionID)

req = Request("https://archive.org/download/" +
              collectionID + "/" + collectionID + "_publication.xml")
try:
    ia_reply = urlopen(req)
except HTTPError as e:
    print('The server couldn\'t fulfill the request.')
    print('Error code: ', e.code)
except URLError as e:
    print('We failed to reach a server.')
    print('Reason: ', e.reason)
else:
    xml_data = xmltodict.parse(ia_reply)
    ad_listings = xml_data['MAGAZINEpublicationGTS']['DocumentStructure']\
        ['DataSets']['Advertisements']['AdIndex']['AdIndexListing']
    advertisers = xml_data['MAGAZINEpublicationGTS']['ContentDepiction']\
        ['DataSets']['Actors']['Organizations']['Organization']


# Utility functions

def split_advertisers(all_advertisers, size):
    for i in range(0, len(all_advertisers), size):
        # Create an index range for l of n items:
        yield all_advertisers[i: i + size]


def ppg2leaf_map_roundup(collectionID):
    global output_dir
    leaf2ppg_map = OrderedDict()
    ppg2leaf_map = OrderedDict()
    # If we have a local ppg2leaf_map, use it. Otherwise long row to hoe...
    ppg2leaf_map_filepath = Path(output_dir + '/' + collectionID + '_ppg2leaf_map.xml')
    if ppg2leaf_map_filepath.is_file():
        # file exists
        with ppg2leaf_map_filepath.open('r') as f:
            raw_map = f.read()
            leaf2ppg_xmlmap = xmltodict.parse(raw_map)['ppg2leaf_map']
            for issue_id in leaf2ppg_xmlmap:
                p2l_map = OrderedDict()
                for xml_leaf, pgNum in leaf2ppg_xmlmap[issue_id].items():
                    leafNum = int(xml_leaf[5:])
                    if pgNum.isdigit():
                        p2l_map[leafNum] = int(pgNum)
                    else:
                        p2l_map[leafNum] = pgNum
                leaf2ppg_map[issue_id] = p2l_map
                ppg2leaf_map[issue_id] = OrderedDict(zip(leaf2ppg_map[issue_id].values(),
                                                         leaf2ppg_map[issue_id].keys()))
    else:
        issues_todo = []
        leaf2ppg_map = OrderedDict()
        leaf2ppg_xmlmap = OrderedDict()
        found_items = internetarchive.search_items('(collection:' + collectionID + ')')
        print("Rounding up issues...")
        for result in found_items:
            issueID = result['identifier']
            print(issueID)
            issues_todo.append(issueID)
            req = Request("https://archive.org/download/" +
                          issueID + "/" + issueID + "_magazine.xml")
            try:
                ia_reply = urlopen(req)
            except HTTPError as e:
                print('The server couldn\'t fulfill the request.')
                print('Error code: ', e.code)
            except URLError as e:
                print('We failed to reach a server.')
                print('Reason: ', e.reason)
            else:
                xml_data = xmltodict.parse(ia_reply)
                # Grab each issue's ppg2leaf_map and add it to the master
                issue_ppg2leaf_map = xml_data['MAGAZINEissueGTS']['DocumentStructure'] \
                    ['DataSets']['ppg2leaf_map']['leaf']
                p2l_skinny_map = OrderedDict()
                p2l_skinnyxml_map = OrderedDict()
                for full_row in issue_ppg2leaf_map:
                    p2l_skinnyxml_map['leaf_' + full_row['@leafnum']] = full_row['pageNum']
                    if full_row['pageNum'].isdigit():
                        p2l_skinny_map[int(full_row['@leafnum'])] = int(full_row['pageNum'])
                    else:
                        p2l_skinny_map[int(full_row['@leafnum'])] = full_row['pageNum']
                leaf2ppg_xmlmap[issueID] = p2l_skinnyxml_map
                leaf2ppg_map[issueID] = p2l_skinny_map
                ppg2leaf_map[issueID] = OrderedDict(zip(leaf2ppg_map[issueID].values(),
                                                        leaf2ppg_map[issueID].keys()))

        # Write the map out locally so we don't have to get it again...
        with ppg2leaf_map_filepath.open('w') as f:
            rooted_ppg2leaf_map = {'ppg2leaf_map': leaf2ppg_xmlmap}
            file_output = xmltodict.unparse(rooted_ppg2leaf_map, pretty=True)
            f.write(file_output)
    return [leaf2ppg_map, ppg2leaf_map]

# Pull together some vital info...
chunked_advertisers = list(split_advertisers(advertisers, 10))
ppg2leaf_maps = ppg2leaf_map_roundup(collectionID)

print("Ready to rumble!!!")


class GetImageThread(Thread):
    """This thread handles getting a leaf image from the Internet Archive
        destined for the pg_queue."""

    def __init__(self, advertiser="", adspec="", issue_id="", leafnum=0, maxheight=0):
        """Init the Worker Thread that queues leaf images."""
        Thread.__init__(self)
        self.advertiser = advertiser
        self.adspec = adspec
        self.issue_id = issue_id
        self.current_leaf = leafnum
        self.maxheight = maxheight
        self.fontname = 'Candrb__.ttf'
        self.daemon = True
        self.start()  # start the thread

    def run(self):
        """Run GetImage Worker Thread to grab an image from the Internet Archive."""
        if self.current_leaf == 'missing':
            self.image_unavailable()
        else:
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
                wx.CallAfter(lambda *a: pub.sendMessage("image_ready", advertiser=self.advertiser,
                                                        adspec=self.adspec, img=image, issue_id=self.issue_id,
                                                        leafnum=self.current_leaf))

    def image_unavailable(self):
        funt = ImageFont.truetype(font='Candrb__.ttf', size=400)
        pil_image = Image.new('RGB', (4200, 5600), 'white')
        dc = ImageDraw.Draw(pil_image)
        dc.text((int((4200-2600)/2), int((5600-600)/2)), "Image Unavailable", font=funt, fill='black')
        # First, do the full-page image...
        resize_percent = self.maxheight / pil_image.size[1]
        wsize = int((float(pil_image.size[0]) * float(resize_percent)))
        pil_sm_image = pil_image.resize((int(wsize), int(self.maxheight)), Image.BICUBIC)
        image = wx.Image(pil_sm_image.size[0], pil_sm_image.size[1])
        image.SetData(pil_sm_image.convert("RGB").tobytes())
        wx.CallAfter(lambda *a: pub.sendMessage("image_ready", advertiser=self.advertiser,
                                                adspec=self.adspec, img=image, issue_id=self.issue_id,
                                                leafnum=self.current_leaf))


class NoFocusButton(buttons.ThemedGenButton):
    def __init__(self, parent, id=wx.ID_ANY, label=wx.EmptyString, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0, validator=wx.DefaultValidator, name=wx.ButtonNameStr):
        buttons.ThemedGenButton.__init__(self, parent, id, label, pos, size, style, validator, name)

    def AcceptsFocusFromKeyboard(self):
        return False # does not accept focus


class Ia_Ad_Ferret_App(wx.App):

    def OnInit(self):
        self.res = xrc.XmlResource('ia_ad_ferret.xrc')
        self.init_frame()
        self.log = sys.stdout
        return True

    def init_frame(self):
        global chunked_advertisers, ppg2leaf_maps, ad_listings
        self.leaf2ppg_map = ppg2leaf_maps[0]
        self.ppg2leaf_map = ppg2leaf_maps[1]
        self.chunked_advertisers = chunked_advertisers
        self.advertiser_chunk = 0
        self.current_advertisers = self.chunked_advertisers[self.advertiser_chunk]
        self.ad_listings = ad_listings
        self.current_advertiser_name = ''
        self.current_advertiser_ads = []
        # Maintains a queue of 10 advertisers to ease navigation through ads
        self.ad_queue = dict()
        #  TODO: Image height offset is hard-coded and needs dynamic fix or user setting
        self.maxheight = wx.GetDisplaySize().Height - 140
        # Start widget stuff...
        self.frame = self.res.LoadFrame(None, 'ID_APPWIN')
        self.frame_title_root = "FactMiners Ad Ferret -- Viewing: "
        self.leafpanel = self.getControl('ID_LEAF_PANEL')
        self.Bind(wx.EVT_LEFT_DOWN, self.evtAdCornerClick_leafpanel)
        # self.leafpanel.Bind(wx.EVT_LEFT_DOWN, self.evtAdCornerClick_leafpanel)
        self.img = wx.StaticBitmap(self.leafpanel, wx.ID_ANY, wx.Bitmap())
        self.widgetbar = self.getControl('ID_WIDGETBAR')
        # Swap out the Help button so it won't accept focus...
        self.structure_sizer = self.widgetbar.GetChildren()[1]
        self.orig_help_btn = self.structure_sizer.GetChildren()[1]
        self.help_btn = NoFocusButton(parent=self.structure_sizer, label='Help', pos=self.orig_help_btn.Position, size=self.orig_help_btn.Size)
        self.orig_help_btn.Hide()
        # self.orig_help_btn.Destroy()
        self.structure_sizer.Layout()
        # self.structure_sizer.Detach(self.help_btn)

        # Get the Products Featured check-listbox hooked up...
        self.products_listbox = self.getControl('ID_PRODUCTS_CHECK_LB')
        self.Bind(wx.EVT_LISTBOX, self.evtProducts_cklb, self.products_listbox)
        self.Bind(wx.EVT_CHECKLISTBOX, self.evtCheckProducts_cklb, self.products_listbox)
        self.products_listbox.SetSelection(0)
        self.products_listbox.Bind(wx.EVT_RIGHT_DOWN, self.onDoHitTest)
        self.addProduct_btn = self.getControl('ID_ADD_PRODUCT_BTN')
        self.Bind(wx.EVT_BUTTON, self.onAddProduct_btn, self.addProduct_btn)
        self.newProduct_txt = self.getControl('ID_ADD_PRODUCT')

        # Menu items and handler bindings...
        self.nextadvertisertaskID = self.getControl('ID_NEXT_ADVERTISER_GROUP_TASK').Id
        self.frame.Bind(wx.EVT_MENU, self.getnext10advertisers, self.getControl('ID_NEXT_ADVERTISER_GROUP_TASK'))
        self.Bind(wx.EVT_MENU, self.getnext10advertisers, None, id=self.nextadvertisertaskID)
        self.prevadvertisertaskID = self.getControl('ID_PREV_ADVERTISER_GROUP_TASK').Id
        self.frame.Bind(wx.EVT_MENU, self.getprev10advertisers, self.getControl('ID_PREV_ADVERTISER_GROUP_TASK'))
        self.Bind(wx.EVT_MENU, self.getnext10advertisers, None, id=self.nextadvertisertaskID)
        self.getgrouptaskID = self.getControl('ID_GET_GROUP_WITH_ADVERTISER_TASK').Id
        self.frame.Bind(wx.EVT_MENU, self.getgroupwithadvertiser, self.getControl('ID_GET_GROUP_WITH_ADVERTISER_TASK'))
        self.Bind(wx.EVT_MENU, self.getnext10advertisers, None, id=self.nextadvertisertaskID)

        self.advertiser_cbox = self.getControl('ID_ADVERTISER')
        self.Bind(wx.EVT_COMBOBOX, self.evtNewAdvertiserSelected, self.advertiser_cbox)
        # TODO: Currently has side-effect of queueing ad leafs, etc...
        self.advertiser_cbox.SetItems(self.get_current_advertiser_names())
        self.advertiser_cbox.SetSelection(0)
        self.current_advertiser_name = self.advertiser_cbox.GetStringSelection()
        self.adlistings_cbox = self.getControl('ID_ADS_COMBOBOX')
        self.Bind(wx.EVT_COMBOBOX, self.evtNewAdListingSelected, self.adlistings_cbox)
        self.adlistings_cbox.SetItems(list(self.get_advertiser_ads(self.current_advertiser_name).keys()))
        self.adlistings_cbox.SetSelection(0)
        # Image grabbing threads post this message and we react...
        pub.subscribe(self.queue_updated, 'image_ready')
        self.issueDate_hilite = self.getControl('wxID_ISSUEDATE')
        self.statusbar = self.getControl('ID_STATUSBAR')

    def queue_updated(self, advertiser, adspec, img, issue_id, leafnum):
        # Get pgNum for this leaf...
        if leafnum == 'missing':
            pg_num = 'img unavailable'
        else:
            pg_num = self.leaf2ppg_map[issue_id][leafnum]
        self.ad_queue[advertiser][adspec]['image'] = img
        if adspec == self.adlistings_cbox.GetStringSelection():
            self.show_ad()
        print('Ad queue added image for ', advertiser, ' on page: ', pg_num, '.')

    def getnextadvertiser(self, event):
        print("Fetchin' next advertiser...")

    def getnext10advertisers(self,event):
        print("Fetchin' next 10 advertisers...")
        self.advertiser_chunk += 1
        self.current_advertisers = self.chunked_advertisers[self.advertiser_chunk]
        self.advertiser_cbox.SetItems(self.get_current_advertiser_names())
        self.advertiser_cbox.SetSelection(0)
        new_advertiser = self.advertiser_cbox.GetStringSelection()
        if new_advertiser != self.current_advertiser_name:
            # print("New advertiser: " + new_advertiser)
            self.current_advertiser_name = new_advertiser
            self.adlistings_cbox.SetItems(list(self.get_advertiser_ads(new_advertiser).keys()))
            self.adlistings_cbox.SetSelection(0)
            self.show_ad()

    def getprev10advertisers(self,event):
        print("Fetchin' previous 10 advertisers...")
        self.advertiser_chunk -= 1
        self.current_advertisers = self.chunked_advertisers[self.advertiser_chunk]
        self.advertiser_cbox.SetItems(self.get_current_advertiser_names())
        self.advertiser_cbox.SetSelection(0)
        new_advertiser = self.advertiser_cbox.GetStringSelection()
        if new_advertiser != self.current_advertiser_name:
            # print("New advertiser: " + new_advertiser)
            self.current_advertiser_name = new_advertiser
            self.adlistings_cbox.SetItems(list(self.get_advertiser_ads(new_advertiser).keys()))
            self.adlistings_cbox.SetSelection(0)
            self.show_ad()

    def getgroupwithadvertiser(self, event):
        # Ask user for the name of the advertiser to be found in a chunked group...
        target_advertiser = self.get_user_input(msg='Advertiser name:', title='Search Advertiser Groups')
        for index, chunk in enumerate(self.chunked_advertisers):
            for advertiser in chunk:
                if advertiser['#text'] == target_advertiser:
                    self.current_advertiser_name = target_advertiser
                    # self.advertiser_chunk = index
                    # self.current_advertisers = self.chunked_advertisers[self.advertiser_chunk]
                    self.current_advertisers = [advertiser]
                    self.advertiser_cbox.SetItems(self.get_current_advertiser_names())
                    cbox_index = self.advertiser_cbox.FindString(target_advertiser)
                    self.advertiser_cbox.SetSelection(cbox_index)
                    self.adlistings_cbox.SetItems(sorted(list(self.get_advertiser_ads(target_advertiser).keys())))
                    self.adlistings_cbox.SetSelection(0)
                    self.show_ad()
                    return
        print('Sorry... did not find that advertiser...')

    def get_user_input(self, parent=None, msg='', title='', default_value=''):
        dlg = wx.TextEntryDialog(parent=parent, message=msg, caption=title, value=default_value)
        dlg.ShowModal()
        result = dlg.GetValue()
        dlg.Destroy()
        return result

    def get_current_advertiser_names(self):
        current_advertiser_names = []
        for advertiser in self.current_advertisers:
            # TODO: Don't yet know how to handle XML w/ ampersand chars, etc....
            current_advertiser_names.append(advertiser['#text'].replace('&amp;', '&'))
        self.queue_ads(current_advertiser_names)
        return current_advertiser_names

    def queue_ads(self, advertiser_names):
        print("Queueing ads...")
        for advertiser in advertiser_names:
            self.get_advertiser_ads(advertiser)

    def get_advertiser_ads(self, advertiser_name):
        # print("Ready to round up ads...")
        this_advertiser_ads = OrderedDict()
        # Round up the ads under the best name...
        for ad_listing in self.ad_listings:
            if ad_listing['#text'] == advertiser_name:
                # Decipher Issue_id for combobox listing
                vol, num, mon, yr = re.sub(r"softalkv(\d)n(\d{2})([a-z]{3})(\d{4})",
                                    r"\g<1>,\g<2>,\g<3>,\g<4>", ad_listing['Issue_id'], 0,
                                    re.MULTILINE).split(',')
                ad_listing_title = '(v.' + str(vol) + 'n.' + str(num) + ') ' + mon.capitalize() + ' ' + yr[2:4] + \
                                   ', page ' + ad_listing['PageNum']
                this_advertiser_ads[ad_listing_title] = ad_listing
        # Check if we have altNames and add their ads...
        for advertiser in self.current_advertisers:
            if advertiser['#text'] == advertiser_name and 'AltName' in advertiser.keys():
                altname = advertiser['AltName']
                if isinstance(altname, str):
                    # Get the ads for this altname
                    for ad_listing in self.ad_listings:
                        if ad_listing['#text'] == altname:
                            # Decipher Issue_id for combobox listing
                            vol, num, mon, yr = re.sub(r"softalkv(\d)n(\d{2})([a-z]{3})(\d{4})",
                                                       r"\g<1>,\g<2>,\g<3>,\g<4>", ad_listing['Issue_id'], 0,
                                                       re.MULTILINE).split(',')
                            ad_listing_title = '(v.' + str(vol) + 'n.' + str(num) + ') ' + mon.capitalize() + ' ' + yr[2:4] + \
                                               ', page ' + ad_listing['PageNum']
                            this_advertiser_ads[ad_listing_title] = ad_listing
                else:
                    # Get the ads for each altname in the list
                    for multi_altname in altname:
                        for ad_listing in self.ad_listings:
                            if ad_listing['#text'] == multi_altname:
                                # Decipher Issue_id for combobox listing
                                vol, num, mon, yr = re.sub(r"softalkv(\d)n(\d{2})([a-z]{3})(\d{4})",
                                                           r"\g<1>,\g<2>,\g<3>,\g<4>", ad_listing['Issue_id'], 0,
                                                           re.MULTILINE).split(',')
                                ad_listing_title = '(v.' + str(vol) + 'n.' + str(num) + ') ' + mon.capitalize() + ' ' + yr[2:4] + \
                                                   ', page ' + ad_listing['PageNum']
                                this_advertiser_ads[ad_listing_title] = ad_listing
        self.ad_queue[advertiser_name] = this_advertiser_ads
        # Let's grab the leafs for these ads! :-)...
        self.get_advertiser_ad_leafs(advertiser_name)
        return this_advertiser_ads

    def getControl(self, xmlid):
        '''Retrieves the given control (within a dialog) by its xmlid'''
        control = self.frame.FindWindowById(xrc.XRCID(xmlid))
        if control is None and self.frame.GetMenuBar() is not None:  # see if on the menubar
            control = self.frame.GetMenuBar().FindItemById(xrc.XRCID(xmlid))
        assert control is not None, 'Programming error: a control with xml id ' + xmlid + ' was not found.'
        return control

    def evtNewAdvertiserSelected(self, event):
        new_advertiser = event.GetString()
        if new_advertiser != self.current_advertiser_name:
            # print("New advertiser: " + new_advertiser)
            self.current_advertiser_name = new_advertiser
            # self.ad_queue = dict()
            self.adlistings_cbox.SetItems(list(self.ad_queue[new_advertiser].keys()))
            self.adlistings_cbox.SetSelection(0)
            self.show_ad()

    def evtNewAdListingSelected(self, event):
        # print("New ad listing selected")
        self.show_ad()

    def evtProducts_cklb(self, event):
        self.log.write('evtProducts_cklb: %s\n' % event.GetString())

    def evtCheckProducts_cklb(self, event):
        index = event.GetSelection()
        label = self.products_listbox.GetString(index)
        status = 'un'
        if self.products_listbox.IsChecked(index):
            status = ''
        self.log.write('Box %s is %schecked \n' % (label, status))
        self.products_listbox.SetSelection(index)  # so that (un)checking also selects (moves the highlight)

    def evtAdCornerClick_leafpanel(self, event):
        """left mouse button is pressed"""
        pt = event.GetPosition()  # position tuple
        if isinstance(event.EventObject, wx.StaticBitmap):
            print(str(pt) + ' : ' + str(event.EventObject.ClientRect.BottomRight))
        event.Skip()

    def onDoHitTest(self, evt):
        item = self.products_listbox.HitTest(evt.GetPosition())
        self.log.write("HitTest: %d\n" % item)

    def onAddProduct_btn(self, evt):
        if self.newProduct_txt.GetValue() != '':
            self.products_listbox.InsertItems([self.newProduct_txt.GetValue()], 0)
            self.products_listbox.Check(0)
            self.products_listbox.SetSelection(0)
            self.newProduct_txt.SetValue('')

    def get_advertiser_ad_leafs(self, advertiser_name):
        get_these_ad_leafs = self.ad_queue[advertiser_name]
        # If we already have the leaf cached locally, don't go get it again...
        for ad in get_these_ad_leafs:
            this_ad_spec = self.ad_queue[advertiser_name][ad]
            # If we already have the leaf cached locally, don't go get it again...
            try:
                this_ad_spec['image']
            except KeyError:
                pgNum = this_ad_spec['PageNum']
                if pgNum.isdigit():
                    pgNum = int(pgNum)
                try:
                    leaf_num = self.ppg2leaf_map[this_ad_spec['Issue_id']][pgNum]
                except KeyError:
                    leaf_num = 'missing'
                    print("Could not get a leaf number for ", this_ad_spec['Issue_id'], ' pgnum: ', pgNum, '.')
                GetImageThread(advertiser=advertiser_name, adspec=ad, issue_id=this_ad_spec['Issue_id'],
                               leafnum=leaf_num, maxheight=self.maxheight)
                print("Getting ad: ", ad)

    def show_ad(self, event=None):
        if event is not None:
            if event.EventObject.Name == 'ID_NEXTAD':
                print("Next ad button clicked.")
                # self.save_spec()
                # self.current_leaf += 1
                # self.advance_queue()
            elif event.EventObject.Name == 'ID_PREVAD':
                print("Previous ad button clicked.")
                # self.save_spec()
                # self.current_leaf -= 1
                # self.retreat_queue()
        # self.check_leaf_btns()

        # if self.current_leaf not in self.pg2leaf_spec.keys():
        #     self.current_leaf += 1
        #     self.showleaf()
        # else:
        #     self.setSpec(self.current_leaf)
        adspec = self.adlistings_cbox.GetStringSelection()
        try:
            self.img.SetBitmap(self.ad_queue[self.current_advertiser_name][adspec]['image'].ConvertToBitmap())
        except KeyError:
            # TODO: Display an 'Image Unavailable' image on the ad_leaf panel.
            print("Image unavailable. The page may be missing from the scanned document, "
                  "or there is a gap in the ppg2leaf map.")
        # self.leafpanel.Refresh()
        #  Size the Frame
        # Get the mon/yr for Issue Date highlight
        mon_yr = re.sub(r"\A\(v\.\dn.\d{2}\)[ ](?P<mon>[ \w]{3})[ ](?P<yr>\d{2}),[ ]page[ ](?P<pgnum>[\w]*)",
                        r"\g<mon>,\g<yr>", adspec, 0, re.MULTILINE)
        mon, yr = mon_yr.split(',')
        self.issueDate_hilite.SetLabel(mon + ' 19' + yr)
        # Size frame before showing ad...
        imgsize = self.img.Size
        x = imgsize[0] + 300
        y = imgsize[1] + 80
        self.frame.Size = (x, y)
        self.frame.Show()


if __name__ == '__main__':
    app = Ia_Ad_Ferret_App(False)
    app.SetTopWindow(app.frame)
    app.frame.Show()
    app.MainLoop()
