#!/usr/bin/env python3

VERSION = "2.0.0-pre2"

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject, Pango
from bs4 import BeautifulSoup as Soup
import urllib.request as ur
import urllib.parse as parse
from threading import Thread
from threading import Timer
import sys
import os.path
import copy
import requests
import time
import json
from html.parser import HTMLParser

GLib.threads_init()

home = os.path.expanduser("~") + "/"
config = home + ".local/share/python-utils/"

# CONFIGURATION
if not os.path.exists(config):
  os.makedirs(config, exist_ok=True)

if not os.path.exists(config + "cc-chat.cfg"):
  # TODO: create the file automatically [#10]
  pass

if not os.path.exists(config + "icons/"):
  os.mkdir(config + "icons/")

if not os.path.exists(config + "icons/cc-chat-icon.png"):
  response = ur.urlopen("https://raw.githubusercontent.com/Fingercomp/" \
    "python-utils/master/icons/cc-chat-icon.png")
  f = open(config + "icons/cc-chat-icon.png", "wb")
  img = response.read()
  f.write(img)
  f.close()

userdata = [i.strip() for i in open(config + "cc-chat.cfg").readlines()]

DELAY = 10
URL = "http://computercraft.ru/index.php?app=shoutbox&module=ajax&section=" \
      "coreAjax&secure_key=" + userdata[0] + "&type=getShouts&lastid=1&" \
      "global=1"
URLSEND = "http://computercraft.ru/index.php?app=shoutbox&module=ajax&" \
          "section=coreAjax&secure_key=" + userdata[0] + "&type=submit&" \
          "lastid=1&global=1"
URLONLINE = "http://computercraft.ru/index.php?app=shoutbox&module=ajax&" \
            "section=coreAjax&secure_key=" + userdata[0] + "&type=getMembers" \
            "&global=1"
HEADERS = {
  "Host": "computercraft.ru",
  "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:42.0) " \
                "Gecko/20100101 Firefox/42.0",
  "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
  "Accept-Language": "en-US,en;q=0.7,ru;q=0.3",
  "Accept-Encoding": "utf-8",
  "Cookie": userdata[1],
  "Connection": "keep-alive",
  "Cache-Control": "max-age=0",
  "Pragma": "no-cache"
}

months = {
  "Январь": "01",
  "Февраль": "02",
  "Март": "03",
  "Апрель": "04",
  "Май": "05",
  "Июнь": "06",
  "Июль": "07",
  "Август": "08",
  "Сентябрь": "09",
  "Октябрь": "10",
  "Ноябрь": "11",
  "Декабрь": "12"
}

lt = "\uf8f0"
gt = "\uf8f1"

root = Gtk.Application()

# http://stackoverflow.com/a/13151299
class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer     = None
        self.interval   = interval
        self.function   = function
        self.args       = args
        self.kwargs     = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        self.function(*self.args, **self.kwargs)
        self.start()

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def cancel(self):
        self._timer.cancel()
        self.is_running = False

class DateTooltip(Gtk.Tooltip):
  
  def __init__(self, text=None, **kwargs):
    super().__init__(**kwargs)
    self.set_text(text)
    self.text = text

  def __call__(self, widget, x, y, keyboard, tooltip):
    if self.text:
      tooltip.set_text(self.text)

    return True


class Chat(Gtk.Window):
  
  def __init__(self):
    super().__init__(title="CC.ru chat client [" + VERSION + "]")
    self.set_default_size(500, 200)

    self.timeout_id = None

    grid = Gtk.Grid(column_spacing=5, row_spacing=5, hexpand=True,
                    vexpand=True)
    grid.set_border_width(5)
    grid.set_column_homogeneous(True)
    self.add(grid)

    frame_chat = Gtk.Frame()

    self.scrlwnd = Gtk.ScrolledWindow()
    self.scrlwnd.set_vexpand(True)
    self.scrlwnd.set_hexpand(True)
    frame_chat.add(self.scrlwnd)
    grid.attach(frame_chat, 1, 1, 8, 10)

    self.chat_box = Gtk.Grid(row_spacing=10)
    self.scrlwnd.add(self.chat_box)
    self.chat_box.set_column_spacing(5)
    self.chat_box.override_background_color(Gtk.StateType.NORMAL,
                                            Gdk.RGBA(1, 1, 1, .8))

    frame_online = Gtk.Frame()

    self.scrlwnd_online = Gtk.ScrolledWindow()
    self.scrlwnd_online.set_vexpand(True)
    self.scrlwnd_online.set_hexpand(False)
    frame_online.add(self.scrlwnd_online)
    grid.attach_next_to(frame_online, frame_chat,
                        Gtk.PositionType.RIGHT, 2, 10)

    self.online_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    self.scrlwnd_online.add(self.online_box)
    self.online_box.override_background_color(Gtk.StateType.NORMAL,
                                              Gdk.RGBA(1, 1, 1, .8))

    self.scrlwnd_online.set_size_request(100, -1)

    self.entry = Gtk.Entry()
    self.entry.connect("activate", self.send_msg)
    grid.attach_next_to(self.entry, frame_chat, Gtk.PositionType.BOTTOM, 8, 1)

    self.btn_send = Gtk.Button(label=">")
    self.btn_send.connect("clicked", self.send_msg)
    grid.attach_next_to(self.btn_send, self.entry,
                        Gtk.PositionType.RIGHT, 1, 1)

    self.btn_upd = Gtk.Button(label="↻")
    self.btn_upd.connect("clicked", self.bh_update)
    grid.attach_next_to(self.btn_upd, self.btn_send,
                        Gtk.PositionType.RIGHT, 1, 1)
    
    self.ind = Gtk.StatusIcon.new()
    self.ind.set_from_file(config + "icons/cc-chat-icon.png")
    self.ind.connect("activate", self.toggle_visibility)

    self.hidden = False
    self.lines = []
    self.old_lines = []
    self.online = []
    self.user_links = {}
    self.updating = False
    self.quitting = False

    self.update_data()
    self.update_gui()

    self.timer_upd = RepeatedTimer(DELAY, self.update_data)
    GLib.timeout_add(1000, self.update_gui)

  def toggle_visibility(self, widget):
    if self.hidden:
      root.release()
      self.set_visible(True)
    else:
      root.hold()
      self.set_visible(False)
    self.hidden = not self.hidden
    return True

  def cursor_fix(self, widget, step_type, step, *args):
    if step == 1:
      widget.get_parent().child_focus(Gtk.DirectionType.RIGHT)
    elif step == -1:
      widget.get_parent().child_focus(Gtk.DirectionType.LEFT)

  def paste_nick(self, widget, event):
    if event.button == 1:
      if event.state & Gdk.ModifierType.CONTROL_MASK == \
          Gdk.ModifierType.CONTROL_MASK:
        nickname = widget.get_text()
        self.entry.do_insert_at_cursor(self.entry, nickname + " ")
        self.entry.grab_focus_without_selecting()
        move_at = self.entry.props.cursor_position + len(nickname) + 1
        self.entry.do_move_cursor(self.entry, Gtk.MovementStep.LOGICAL_POSITIONS, move_at, False)
      elif event.state & Gdk.ModifierType.MOD1_MASK == \
          Gdk.ModifierType.MOD1_MASK:
        link = ""
        try:
          link = self.user_links[widget.get_text()[1:]]
        except:
          pass
        if link != "":
          Gtk.show_uri(None, link, Gdk.CURRENT_TIME)
    return True

  def bh_quit(self, widget=None, *args):
    self.quitting = True
    while self.updating is True:
      time.sleep(0.05)
    self.timer_upd.cancel()
    Gtk.main_quit()

  def update_data(self, widget=None):
    if self.quitting is True:
      return False
    if self.updating is False:
      self.updating = True
      self.lines = []
      self.online = []
      request = ur.Request(URL, headers=HEADERS)
      response = ur.urlopen(request).read()
      page = response.decode("utf-8")
      html = Soup(page, "html.parser")
      rows = html.find_all("tr")
      for row in rows:
        blocks = row.find_all("td")
        author = blocks[0].find(class_="at_member")["data-store"]
        author_short = author[:]
        if len(author) > 16:
          author_short = author[:16] + "…"
        author_url = blocks[0].find("a", class_="_hovertrigger")["href"]
        date = [i for i in blocks[2].find("span", class_="right").strings][0] \
                .strip()[1:-1]
        date_arr = date.split(" ")
        month = months[date_arr[1]]
        date = date_arr[2] + "-" + month + "-" + date_arr[0] + " " + date_arr[4]
        date_short = date_arr[4]
        raw_msg = blocks[2].find("span", class_="shoutbox_text").p
        
        for tag in raw_msg.find_all("img"):
          tag.replace_with(tag["alt"])

        for tag in raw_msg.find_all("a"):
          tag.replace_with(lt + "a href=\"" + tag["href"] + "\" title=\"" + \
            tag["title"] + "\"" + gt + tag.string + lt + "/a" + gt)

        for tag in raw_msg.find_all("strong"):
          tag.replace_with(lt + "b" + gt + tag.string + lt + "/b" + gt)

        for tag in raw_msg.find_all("em"):
          tag.replace_with(lt + "i" + gt + tag.string + lt + "/i" + gt)

        for tag in raw_msg.find_all("span", style="color: black; " + \
          "font-family: courier; background-color: #EAEAEA"):
          tag.replace_with(lt + "span background=\"gray\" " + \
            "foreground=\"white\"" + gt + tag.string + lt + "/span" + gt)
  
        msg = "".join([i for i in blocks[2] \
                .find("span", class_="shoutbox_text").p.strings])
        html_parser = HTMLParser()
        msg = html_parser.unescape(msg)
        msg = msg.replace("&", "&amp;")
        msg = msg.replace("<", "&lt;")
        msg = msg.replace(">", "&gt;")
        msg = msg.replace(lt, "<")
        msg = msg.replace(gt, ">")
        self.lines.append({"author": author, "author_short": author_short,
                           "url": author_url, "date": date,
                           "date_short": date_short, "msg": msg})
        self.user_links[author] = author_url
      request = ur.Request(URLONLINE, headers=HEADERS)
      response = json.loads(ur.urlopen(request).read().decode("utf-8"))
      for user in response["NAMES"]:
        html = Soup(user, "html.parser")
        member = None
        member_code = html.find("span")
        if member_code:
          member_links = html.find("span").find_all("a")
          for link in member_links:
            test = None
            try:
              test = link["onclick"]
            except:
              pass
            if not test:
              member = link
          member_url = member["href"]
          member = member.string
        else:
          member = user
        member_url = "http://computercraft.ru/"
        self.online.append({"user": member, "url": member_url})
        #self.user_links[member] = member_url

      self.updating = False

  def update_gui(self, widget=None):
    if self.updating is False:
      self.btn_upd.set_sensitive(True)
      if self.lines != self.old_lines:
        prev = None
        for child in self.chat_box.get_children():
          child.destroy()
        test = Gtk.Label("") # Kashdil!
        test.set_selectable(True)
        test.modify_font(Pango.FontDescription("sans 1"))
        self.chat_box.add(test)
        for line in self.lines:
          label_user = Gtk.Label("@" + line["author_short"])
          tooltip_user = DateTooltip(text=line["author"])
          label_user.set_has_tooltip(True)
          label_user.connect("query-tooltip", tooltip_user)
          label_user.connect("button-press-event", self.paste_nick)
          label_msg = Gtk.Label()
          label_msg.set_markup(line["msg"])
          label_date = Gtk.Label(line["date_short"])
          tooltip_date = DateTooltip(text=line["date"])
          label_date.set_has_tooltip(True)
          label_date.connect("query-tooltip", tooltip_date)
          label_user.set_line_wrap(True)
          label_msg.set_line_wrap(True)
          label_date.set_line_wrap(True)
          label_user.set_justify(Gtk.Justification.RIGHT)
          label_msg.set_justify(Gtk.Justification.LEFT)
          label_date.set_justify(Gtk.Justification.RIGHT)
          label_msg.set_xalign(0)
          label_msg.set_yalign(0)
          label_user.set_xalign(0)
          label_user.set_yalign(0)
          label_user.set_selectable(True)
          label_msg.set_selectable(True)
          label_date.set_selectable(True)
          label_user.connect("move-cursor", self.cursor_fix)
          label_msg.connect("move-cursor", self.cursor_fix)
          label_date.connect("move-cursor", self.cursor_fix)
          if not prev:
            self.chat_box.add(label_user)
          else:
            self.chat_box.attach_next_to(label_user, prev,
                                         Gtk.PositionType.BOTTOM, 1, 1)
          self.chat_box.attach_next_to(label_msg, label_user,
                                       Gtk.PositionType.RIGHT, 1, 1)
          self.chat_box.attach_next_to(label_date, label_msg,
                                       Gtk.PositionType.RIGHT, 1, 1)
          label_user.show()
          label_msg.show()
          label_date.show()
          prev = label_user
        self.old_lines = copy.deepcopy(self.lines)
      for child in self.online_box.get_children():
        child.destroy()
      online_label = Gtk.Label("")
      online_label.set_markup("<span foreground=\"gray\">Online</span>")
      online_label.set_xalign(.5)
      online_label.set_yalign(.5)
      online_label.set_justify(Gtk.Justification.CENTER)
      self.online_box.add(online_label)
      online_label.show()
      for user in self.online:
        label = Gtk.Label(user["user"])
        label.set_xalign(0)
        label.set_yalign(0)
        label.set_justify(Gtk.Justification.LEFT)
        self.online_box.add(label)
        label.show()
    else:
      self.btn_upd.set_sensitive(False)
    return True
  
  def bh_update(self, widget=None):
    self.thread_upd = Thread(target=self.update_data)
    self.thread_upd.start()

  def send_msg(self, widget=None):
    self.sending = True
    self.btn_send.set_sensitive(False)
    self.entry.set_progress_pulse_step(0.2)
    self.timeout_progress_entry = GObject.timeout_add(100, self.do_pulse, None)
    msg = self.entry.get_text()
    self.thread_send = Thread(target=self.send_msg_thread, args=(msg,))
    self.thread_send.start()
    self.timeout_check_sent = GObject.timeout_add(500, self.check_sent)

  def do_pulse(self, *args):
    self.entry.progress_pulse()
    return True

  def check_sent(self, *args):
    if self.sending == False:
      self.btn_send.set_sensitive(True)
      GObject.source_remove(self.timeout_progress_entry)
      self.timeout_progress_entry = None
      self.entry.set_progress_pulse_step(0)
      self.entry.set_text("")
      self.bh_update()
      self.update_gui()
      return False
    return True

  def send_msg_thread(self, msg):
    post_data = parse.quote(parse.quote(msg, safe=""), safe="")
    headers = copy.deepcopy(HEADERS)
    headers["Referer"] = "http://computercraft.ru/"
    headers["X-Requested-With"] = "XMLHttpRequest"
    headers["X-Prototype-Version"]= "1.7.1"
    headers["Content-Type"] = "application/x-www-form-urlencoded; " \
                              "charset=UTF-8"
    headers["Accept-Encoding"] = "gzip, deflate"
    headers["Accept"] = "text/javascript, text/html, application/xml, " \
                        "text/xml, */*"
    headers["Cache-Control"] = "no-cache"
    r = requests.post(URLSEND, headers=headers, data={"shout": post_data})
    self.sending = False


win = Chat()
win.connect("delete-event", win.bh_quit)
win.show_all()
Gtk.main()

# vim: set autoindent tabstop=2 shiftwidth=2 expandtab:
