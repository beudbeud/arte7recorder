#!/usr/bin/env python 
# -*- coding: utf-8 -*-


import sys
import os, subprocess, shutil, select
import signal
import gtk
import gobject
import gtk.glade
import re
import urllib2, xml.dom.minidom
import pynotify 
import ConfigParser
import locale
import gettext
import pygtk
import BeautifulSoup as BS
pygtk.require('2.0')

from Catalog import Catalog, unescape_html, get_lang


APP = "messages"
DIR = "locale"
subprocess_pid = None

gtk.glade.bindtextdomain(APP, DIR)
gtk.glade.textdomain(APP)
pathname = os.path.dirname(sys.argv[0])
localdir = os.path.abspath(pathname) + "/locale"
gettext.install("messages", localdir)


def unescape_xml(text):
    text = text.replace( "%3A", ":").replace( "%2F", "/").replace( "%2C", ",")
    return BS.BeautifulStoneSoup(text, convertEntities=BS.BeautifulStoneSoup.XML_ENTITIES).contents[0]

def get_rtmp_url( url_page, quality ):
    page_soup = BS.BeautifulSoup( urllib2.urlopen(url_page).read() )

    movie_object = page_soup.find("object", classid="clsid:d27cdb6e-ae6d-11cf-96b8-444553540000")
    movie = movie_object.find("param", {"name":"movie"})
    movie_url = "http" + unescape_xml(movie['value'].split("http")[-1])

    xml_soup = BS.BeautifulStoneSoup( urllib2.urlopen(movie_url).read() )
    movie_url = xml_soup.find("video", {'lang': get_lang()})['ref']

    xml_soup = BS.BeautifulStoneSoup( urllib2.urlopen(movie_url).read() )
    base_soup = xml_soup.find("urls")
    movie_url = base_soup.find("url", {"quality": quality}).string
    return movie_url

def rtmp_download( link, destination = "/dev/null", try_resume = True, resuming =False ):
    global subprocess_pid
    some_dl_done = False
    need_more_dl = True
    if try_resume and os.path.isfile( destination ):
        for percent in rtmp_download(link, destination, False, True ):
            if percent != -1:
                some_dl_done = True
                need_more_dl = percent != 100.0
                yield percent
            else:
                break

    destination = destination.encode(sys.getfilesystemencoding(), 'ignore')

    cmd_dl = 'flvstreamer -r "%s" --flv "%s"' % (link, destination)
    cmd_resume = 'flvstreamer -r "%s" --resume --flv "%s"' % (link, destination)
    cmd_resume_skip = 'flvstreamer -r "%s" --resume --skip 1 --flv "%s"' % (link, destination)
    SECONDS_TO_WAIT = 3
    max_skip_cnt = 10
    percent_re = re.compile("\((.+)%\)$")

    ret_code = None
    if some_dl_done or resuming:
        cmd = cmd_resume
    else:
        cmd = cmd_dl
    while need_more_dl:
        stderr_buff = ""
        whole_stderr_buff = ""
        p = subprocess.Popen( cmd, shell=True, stderr=subprocess.PIPE, close_fds=True)
        subprocess_pid = p.pid + 1
        while ret_code is None:
            fds_read, fds_write, fds_exception = select.select([p.stderr],[], [], SECONDS_TO_WAIT)
            if len(fds_read) == 1:
                c = p.stderr.read(1)
                whole_stderr_buff += c
                if c in ("\n","\r"):
                    match = percent_re.search( stderr_buff )
                    if match is not None:
                        # If anyframe was retreived, then reset available skip count
                        max_skip_cnt = 10
                        yield float(match.group(1))
                    stderr_buff = ""
                else:
                    stderr_buff += c
            ret_code = p.poll()
        whole_stderr_buff += p.stderr.read()
        subprocess_pid = None
        if ret_code == 0:
            yield 100.0
            break
        elif ret_code == 2:
            cmd = cmd_resume
        else:
            must_resume = False
            for line in whole_stderr_buff.split("\n"):
                if line.find("Couldn't resume FLV file, try --skip 1") != -1:
                    must_resume = True
                    break
            if must_resume and max_skip_cnt >= 0:
                max_skip_cnt -= 1
                cmd = cmd_resume_skip
            else:
                print ret_code
                print whole_stderr_buff
                print
                yield -1.0
        ret_code = None



class GUI(object):
  wmvRE = re.compile('availableFormats.*=.*"(.*HQ.*wmv.*)"')
  mmsRE = re.compile('"(mms.*)"')
  resumeRE = re.compile('<p class="text">([^<]*)<')
  dureeRE = re.compile('[^0-9]*([0-9]+)(mn|min)')
        
  def __init__(self):
      self.staticon = gtk.StatusIcon() 
      self.staticon.set_from_file("/usr/share/pixmaps/arte-icon.png") 
      self.staticon.connect("activate", self.activate) 
      self.staticon.connect("button-press-event", self.menuquit) 
      self.staticon.set_visible(True) 
      self.reduce_window = False
      self.first = None
      self.startup = True
      self.builder = gtk.Builder()
      self.builder.add_from_file("./Arte7recorderWindow.ui")
      self.builder.connect_signals(self)
      self.window1 = self.builder.get_object("arte7recorder_window")
      self.window1.maximize()
      self.emi_dispo()
      self.emi_dl()
      self.vbox2 = self.builder.get_object("vbox2")
      self.frame4 = self.builder.get_object("frame4")
      self.bouton_del = self.builder.get_object("bouton_del")
      self.menu_play = self.builder.get_object("menucontext_play")
      self.contextQuit = self.builder.get_object("contextQuit") 
      self.dirconf = os.path.expanduser('~') + '/.arteplus7'
      self.config = ConfigParser.RawConfigParser()
      if os.path.isdir(self.dirconf) == False:
          os.mkdir(self.dirconf)
          self.first = 'yes'
      self.fileconf = os.path.expanduser('~/.arteplus7/.config.cfg')
      if os.path.isfile(self.fileconf) == True:
          self.config.read(self.fileconf)
          self.directory = self.config.get('Repertoire', 'dir')
          self.player = self.config.get('Player', 'player')
          if self.player == "0":
              self.valueplayer = "totem"
          elif self.player == "1":
              self.valueplayer = "vlc"
          elif self.player == "2":
              self.valueplayer = "mplayer"
      else:
          self.welcom = self.builder.get_object("welcom")
          self.welcom.show()
      if self.first == 'yes':
          self.window1.hide()  
      else: 
          self.window1.show()
          self.dl_resume(None, None, None)
          
  def destroy_wl(self, widget, data=None):
      self.welcom.hide()
      
  def activate( self, widget, data=None): 
      if self.reduce_window == False:
        self.window1.hide() 
        self.reduce_window = True
      else:
        self.window1.show() 
        self.reduce_window = False
        
  def menuquit(self, button, event):
     if event.button == 3:
          self.contextQuit.popup(None, None, None, event.button, event.time)    
      
  #Bouton Refresh
  def on_actu(self, button):
      catalog
      datalist = open('/tmp/database', 'w')
      print >> datalist, '\n'.join(['%s;%s;%s;%s' % (video[Catalog.TITLE_TAG], video[Catalog.DATE_TAG], video[Catalog.URL_TAG], video[Catalog.IMAGE_TAG]) for video in  catalog.videos])
      datalist.close()
      self.liststore.clear()
      f = open ("/tmp/database", "r")
      for line in f:
          t = line.split(";")
          self.liststore.append([t[0], t[1], t[2], t[3]])   

  #Bouton About
  def about(self, widget):
      self.builder.add_from_file("./Arte7recorderWindow.ui")
      self.about = self.builder.get_object("arte7recorder_about")
      self.result = self.about.run()
      self.about.destroy()
      return self.result
      
  #Bouton Preference    
  def preferences(self, widget):
      self.builder.add_from_file("./Arte7recorderWindow.ui")
      self.pref = self.builder.get_object("arte7recorder_pref")
      if self.first == 'yes':        
          self.restart = self.builder.get_object("label12") 
          self.restart.show()
      self.chplayer = self.builder.get_object("combobox1")
      self.chdir = self.builder.get_object("filechooserbutton1")
      self.chdir.set_current_folder(os.path.expanduser('~/'))
      if os.path.isfile(self.fileconf) == True:
          self.config.read(self.fileconf)
          self.directory = self.config.get('Repertoire', 'dir')
          self.player = self.config.get('Player', 'player')
          play = int(self.player)
          self.chplayer.set_active(play)
          self.chdir.set_filename(self.directory)
      self.result = self.pref.run()
      if self.result == 0:
          try: 
              self.config.add_section('Repertoire')
              self.config.add_section('Player')         
          except ConfigParser.DuplicateSectionError:
              print ""
          finally:
              self.config.set('Repertoire', 'dir', self.chdir.get_filename())
              self.config.set('Player', 'player', self.chplayer.get_active())
              fileconfig = os.path.expanduser('~/.arteplus7/.config.cfg')
              with open(fileconfig, 'wb') as configfile:
                  self.config.write(configfile)
              self.config.read(self.fileconf)
              self.directory = self.config.get('Repertoire', 'dir')
              self.player = self.config.get('Player', 'player')   
              if self.player == "0":
                  self.valueplayer = "totem"
              elif self.player == "1":
                  self.valueplayer = "vlc"
              elif self.player == "2":
                  self.valueplayer = "mplayer"   
      self.pref.destroy()
      return self.result
      
  #Bouton Quit
  def quit(self, widget, data=None):
      self.main_quit()

  def on_destroy(self, widget, data=None):
      gtk.main_quit()
   
  #Bouton + 
  def on_add_emi(self, bouton):
   	  selection = self.treeview_disp.get_selection()
          modele, iter = selection.get_selected()
          data_nom = modele.get_value(iter, 0)
          data_date = modele.get_value(iter, 1)
          data_url = modele.get_value(iter, 2)
          self.liststore2.append([data_nom, data_date, data_url, _("Waiting")])
          self.frame4.show()
          self.bouton_del.show()
          return

  #Bouton -
  def on_del_emi(self, bouton):
      selection = self.treeview_dl.get_selection()
      modele, iter = selection.get_selected()
      if iter:
          modele.remove(iter)
      return

  #Notification
  def notify(self):
     img_uri = "/usr/share/pixmaps/arte-icon.png"
     pynotify.init("Arte+7 Recorder")
     notification = pynotify.Notification(self.nom_emi, _("Download complete"), img_uri)
     notification.show()

  #Download
  def on_telecharge(self, bouton):
          self.treeiter = self.liststore2.get_iter_first()
          self.bouton_dl = self.builder.get_object("bouton_dl")
          self.annuler = self.builder.get_object("button3")
          self.menu_ann = self.builder.get_object("menucontext_ann")
          self.menu_clean = self.builder.get_object("menucontext_clean")
          self.annuler.show()
          self.bouton_dl.hide()
          self.menu_play.set_sensitive(True)
          self.menu_ann.set_sensitive(True)
          self.menu_clean.set_sensitive(True)
          self.treeview_dl.set_reorderable(False)
          self.clic_annuler_all = None
          for n in self.liststore2:
              if self.liststore2.get_value(self.treeiter, 3) == _('Complete'):
                  self.treeiter = self.liststore2.iter_next(self.treeiter)
                  continue
              self.clic_annuler = None
              if self.clic_annuler_all == "stopdl_all":
                  self.liststore2.set_value(self.treeiter, 3, _('Cancel')) 
                  break
              url_page = n[2]
              self.nom_emi = n[0]
              self.nom_fichier = self.nom_emi + "-" + n[1] + '.flv'
              self.nom_fichier = self.nom_fichier.replace("/", "-")
              self.liststore2.set_value(self.treeiter, 3, _('Download...'))
              try:
                  rtmp_url = get_rtmp_url( url_page, quality = "hd"  )
                  signal_fin = False
                  for percent in rtmp_download( rtmp_url, self.directory + "/" + self.nom_fichier.replace("'", "_") ):
                      if percent == -1.0:
                          raise IOError()
                      signal_fin = percent == 100.0
                      if self.clic_annuler == "stopdl":
                          if subprocess_pid is not None:
                              os.kill( subprocess_pid, signal.SIGINT )
                          self.liststore2.set_value(self.treeiter, 3, _('Canceled at ')+str(percent)) 
                          break
                      else:
                          self.liststore2.set_value(self.treeiter, 3, str(percent)+"%" )
                      # affichage de la progression
                      while gtk.events_pending():
                          gtk.main_iteration()
              except IOError:
                  self.builder.add_from_file("./Arte7recorderWindow.ui")
                  self.erreur = self.builder.get_object("error_dialog")
                  self.error_text = self.builder.get_object("error_text")
                  self.error_text.set_text(_("There are problem with your internet connection"))
                  self.erreur.run()
                  self.result = self.erreur.run()
                  self.erreur.destroy()
              else:
                  if signal_fin and self.clic_annuler_all == None and self.clic_annuler == None:
                      self.notify()
                      self.liststore2.set_value(self.treeiter, 3, _('Complete'))
                  self.treeiter = self.liststore2.iter_next(self.treeiter)
          self.treeview_dl.set_reorderable(True)
          self.annuler.hide()
          self.bouton_dl.show()
              
  #Download
  def on_cancel(self, bouton):
      self.clic_annuler = "stopdl"
      self.clic_annuler_all = "stopdl_all"
      self.menu_ann.set_sensitive(False)
      self.liststore2.set_value(self.treeiter, 3, _('Cancel')) 
      self.annuler.hide()
      self.bouton_dl.show()
                   
  #Tableau des emissions disponible
  def emi_dispo(self):
      self.treeview_disp = self.builder.get_object("treeview_disp")          
      self.liststore = gtk.ListStore(str, str, str, str)
      self.treeview_disp.set_model(self.liststore)
      self.columnNom = gtk.TreeViewColumn(_("Name"))
      self.columnNom.set_sort_column_id(0)
      self.columnDate = gtk.TreeViewColumn(_("Date"))
      self.columnDate.set_sort_column_id(1)
      self.columnUrl = gtk.TreeViewColumn(_("Url"))
      self.columnImage = gtk.TreeViewColumn(_("Picture"))
      self.treeview_disp.append_column(self.columnNom)
      self.treeview_disp.append_column(self.columnDate)
      self.treeview_disp.append_column(self.columnUrl)
      self.treeview_disp.append_column(self.columnImage)
      self.columnUrl.set_visible(False)
      self.columnImage.set_visible(False)
      self.cellNom = gtk.CellRendererText()
      self.cellDate = gtk.CellRendererText()
      self.cellUrl = gtk.CellRendererText()
      self.cellImage = gtk.CellRendererText()
      self.columnNom.pack_start(self.cellNom, True)
      self.columnDate.pack_start(self.cellDate, False)
      self.columnUrl.pack_start(self.cellUrl, False)
      self.columnImage.pack_start(self.cellImage, False)
      self.columnNom.add_attribute(self.cellNom, 'text', 0)
      self.columnDate.add_attribute(self.cellDate, 'text', 1)
      self.columnUrl.add_attribute(self.cellUrl, 'text', 2)
      self.columnImage.add_attribute(self.cellImage, 'text', 3)
      #self.columnDate.set_sort_column_id(1)
      self.treeview_disp.set_search_column(0)
      #self.treeview_disp.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
      f = open ("/tmp/database", "r")
      for line in f:
          t = line.split(";")
          self.liststore.append([t[0], t[1], t[2], t[3]])

  #Téléchargement du résumé et de l'image
  def dl_resume(self, treeview_disp, path, columnNom):
      if self.startup == True:
          iter = self.liststore.get_iter_first()
          modele = self.liststore
          self.startup = False
      else:
          selection = self.treeview_disp.get_selection()
          modele, iter = selection.get_selected()
      data_url = modele.get_value(iter, 2)
      data_nom = modele.get_value(iter, 0)
      data_date = modele.get_value(iter, 1)
      data_image = modele.get_value(iter, 3)
      self.label6 = self.builder.get_object("label6")
      self.label6.set_text(data_nom)
      self.label7 = self.builder.get_object("label7")
      self.label7.set_text(data_date)
      page = urllib2.urlopen(data_url).read()
      #data_resume = self.resumeRE.search(page).group(1).replace('\n', '').strip()
      soup = BS.BeautifulSoup( page )
      base_node = soup.find('div', {"class":"recentTracksCont"})
      data_resume = u""
      for i in base_node.findAll('p'):
          if len(data_resume) != 0:
              data_resume += "\n"
          #print data_resume.replace("\n","\\n"), i.string
          try:
              data_resume += unescape_html(i.string)
              if i["class"] == "accroche":
                  data_resume += "\n"
          except:
              pass
      self.textbuffer1 = self.builder.get_object("textbuffer1")
      self.textbuffer1.set_text(data_resume)
      data_time = self.dureeRE.search(page).group(1)
      self.label13 = self.builder.get_object("label13")
      self.label13.set_text(data_time + " min")
      f = urllib2.urlopen(data_image)
      local = open("/tmp/image.jpg", 'wb')
      local.write(f.read())
      local.close()
      self.image_emi = self.builder.get_object("image_emi")
      self.image_emi.set_from_file("/tmp/image.jpg")
      
  def show_context_menu(self, button, event):
      if event.button == 3:
          self.contextMenu.popup(None, None, None, event.button, event.time)      

  def on_menucontext_play(self, widget):
      selection = self.treeview_dl.get_selection()
      modele, iter = selection.get_selected()
      data_nom = modele.get_value(iter, 0)
      data_date = modele.get_value(iter, 1)
      command = "'%s' '%s'" % (self.valueplayer, self.directory + "/" + data_nom + "-" + data_date + ".flv".replace("'", "_"))
      self.process_play = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
      
  def on_menucontext_ann(self, widget):
      self.clic_annuler = "stopdl"
      self.liststore2.set_value(self.treeiter, 3, _('Cancel')) 
      
  def on_menucontext_clean(self, widget):
      print "Todo"
               
  #Tableau des emissions sélectionnées
  def emi_dl(self):
      self.treeview_dl = self.builder.get_object("treeview_dl")
      self.liststore2 = gtk.ListStore(str, str, str, str)
      self.treeview_dl.set_model(self.liststore2)
      self.treeview_dl.set_reorderable(True)
      self.columnNom2 = gtk.TreeViewColumn (_("Name"))
      self.columnDate2 = gtk.TreeViewColumn (_("Date"))
      self.columnUrl2 = gtk.TreeViewColumn (_("Url"))
      self.columnProgress = gtk.TreeViewColumn (_("Progress"))
      self.treeview_dl.append_column(self.columnNom2)
      self.treeview_dl.append_column(self.columnDate2)
      self.treeview_dl.append_column(self.columnUrl2)
      self.treeview_dl.append_column(self.columnProgress)
      self.columnUrl2.set_visible(False)
      self.cellNom2 = gtk.CellRendererText()
      self.cellDate2 = gtk.CellRendererText()
      self.cellUrl2 = gtk.CellRendererText()
      self.cellProgress = gtk.CellRendererText()
      self.columnNom2.pack_start(self.cellNom2, True)
      self.columnDate2.pack_start(self.cellDate2, False)
      self.columnUrl2.pack_start(self.cellUrl2, False)
      self.columnProgress.pack_start(self.cellProgress, False)
      self.columnNom2.add_attribute(self.cellNom2, 'text', 0)
      self.columnDate2.add_attribute(self.cellDate2, 'text', 1)
      self.columnUrl2.add_attribute(self.cellUrl2, 'text', 2)
      self.columnProgress.add_attribute(self.cellProgress, 'text', 3) 
      self.contextMenu = self.builder.get_object("contextMenu")  
      self.treeview_dl.connect("button-press-event", self.show_context_menu)
      

if __name__ == "__main__":
  catalog = Catalog()
  datalist = open('/tmp/database', 'w')
  print >> datalist, '\n'.join(['%s;%s;%s;%s' % (video[Catalog.TITLE_TAG], video[Catalog.DATE_TAG], video[Catalog.URL_TAG], video[Catalog.IMAGE_TAG]) for video in  catalog.videos])
  datalist.close()
  app = GUI()
  gtk.main()
  

