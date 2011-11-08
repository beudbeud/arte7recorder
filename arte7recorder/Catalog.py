#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, re
import time
import urllib2, xml.dom.minidom
import sys
#import gconf
import BeautifulSoup as BS

def unescape_html(text):
    return BS.BeautifulStoneSoup(text, convertEntities=BS.BeautifulStoneSoup.HTML_ENTITIES).contents[0]

def get_lang():
    lang = os.environ.get("LANG")
    n = lang.split('_')
    lang = "fr"
    if n[0] in ("fr","de"):
        lang = n[0]
    return lang

time_re = re.compile("^\d\d[h:]\d\d$")
fr_monthes = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
de_monthes = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
def parse_date( date_str ):
    date_array = date_str.split(",")
    if time_re.search( date_array[-1].strip() ) is None:
        return ""
    time_ = date_array[-1].strip()
    if date_array[0].strip() in ("Aujourd'hui", "Heute"):
        date_ = time.strftime( "%Y %m %d" )
    elif date_array[0].strip() in ("Hier", "Gestern"):
        date_ = time.strftime( "%Y %m %d", time.localtime(time.time() - (24*60*60)) )
    else:
        array = date_array[1].split()
        day = array[0].strip(".")
        month = array[1]
        for arr in (fr_monthes, de_monthes):
            if array[1] in arr:
                month = "%02d" % (arr.index(array[1])+1)
        year = array[2]
        date_ = "%s %s %s" % (year, month, day)
    #print date_ + ", " + time_
    return date_ + ", " + time_

class Catalog:

  # Constantes
  ARTE_WEB_ROOT = 'http://arte7.arte.tv'
  ARTE_WEB_ROOT = 'http://videos.arte.tv'
  INDEX_TAG = 'index'
  TITLE_TAG = 'bigTitle'
  DATE_TAG = 'startDate'
  URL_TAG = 'targetURL'
  MMS_TAG = 'mmsURL'
  RESUME_TAG = 'resume'
  IMAGE_TAG = 'previewPictureURL'
  
  # Contenu du catalogue
  videos = []
  # Expressions régulières utilisée pour la recherche dans les pages web
  xmlRE = re.compile('xmlURL", "(.*\.xml)"')
  wmvRE = re.compile('availableFormats.*=.*"(.*HQ.*wmv.*)"')
  mmsRE = re.compile('"(mms.*)"')
  resumeRE = re.compile('<p class="text">([^<]*)<')

  def __init__(self):
    lang = "/%s/" % get_lang()
    max_video_displayed = 200 #Maximum number of videos to display
    self.error = False
    try:
        base_page_url = self.ARTE_WEB_ROOT + lang + "videos/" 
        #we first load the page in order to get the page url 
        #with the correct index
        html_content = urllib2.urlopen( base_page_url ).read() 
        soup = BS.BeautifulSoup( html_content )
        
        found_url = 0
        for j in soup.findAll('script'): 
            #we will look for the script in the page that has the url 
            #with the correct index
            for text in j:
                if "videowallSettings" in text: 
                    #when the script is found, we will collect the url
                    for word in text.split():
                        if "asThumbnail" in word: 
                            #there are 4 different urls, we want the one 
                            #that displays thumbnails
                            base_page_url = self.ARTE_WEB_ROOT + \
                                        word.replace('"','')  + "?hash=" + \
                                        lang.replace('/','') + "/thumb///1/"\
                                        + str(max_video_displayed) + "/"
                            found_url = 1
                            break
                if found_url:
                    break
            if found_url:
                break
                                                
        html_content = urllib2.urlopen( base_page_url ).read() 
        soup = BS.BeautifulSoup( html_content )
        for i in soup.findAll('div', {"class":"video"}):
            print "i.prettify", i.prettify()
            video = dict()
            for h in i.findAll('h2'):
                for a in h.findAll('a'):
                    video['targetURL'] = self.ARTE_WEB_ROOT + a['href']
                    video['targetURL'] = video['targetURL'].replace("/fr/", lang)
                    try:
                        video['bigTitle'] = unescape_html( a.string )
                    except:
                        video['bigTitle'] = "Unknow"
            for p in i.findAll('p'):
                if 'class' in p:
                    if p['class'] == 'teaserText':
                        video['summary'] = p.string
                else:
                    if p.string != "" and not p.string.endswith("vues") \
                                        and not p.string.endswith("Aufrufe"):
                        video['startDate'] = parse_date( p.string )
            #get thumbnail image:
            for t in i.findAll( 'img', {"class":"thumbnail"}):
                #print t
                video['previewPictureURL'] = self.ARTE_WEB_ROOT + t['src']
                video['previewPictureURL'] = video['previewPictureURL']\
                                        .replace("/fr/", lang)
            #print video
            self.videos.append(video)
            #break
        
    except Exception, why:
        self.error = why




