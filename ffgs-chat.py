#!/usr/bin/env python3

VERSION = "1.9"

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject
from threading import Thread
from threading import Timer
import sys
import os.path
import copy
import requests
import json
import time

GLib.threads_init()

userdata = [i.strip() for i in open(
              os.path.expanduser("~") + \
              "/.config/ffgs-chat.cfg").readlines()]

DELAY = 10
URLGET = "http://ffgs.ru/chat/getmsg?id=1"
URLSEND = "http://ffgs.ru/chat/say"
URLONLINE = "http://ffgs.ru/chat/getonline"
URLUSER = "http://ffgs.ru/chat/getuser"
HEADERS = {
  "Cookie": "PHPSESSID=" + userdata[0]
}

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
    if text:
      self.set_text(text)
    self.text = text

  def __call__(self, widget, x, y, keyboard, tooltip):
    if self.text:
      tooltip.set_text(self.text)

    return True


class Chat(Gtk.Window):
  
  def __init__(self):
    Gtk.Window.__init__(self, title="FFGS chat client [" + VERSION + "]")
    self.set_default_size(500, 200)

    self.timeout_id = None

    grid = Gtk.Grid(column_spacing=5, row_spacing=5,
                    hexpand=True, vexpand=True)
    grid.set_border_width(5)
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
    self.chat_box.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(1, 1, 1, .8))

    frame_online = Gtk.Frame()

    self.scrlwnd_online = Gtk.ScrolledWindow()
    self.scrlwnd_online.set_vexpand(True)
    self.scrlwnd_online.set_hexpand(True)
    frame_online.add(self.scrlwnd_online)
    grid.attach_next_to(frame_online, frame_chat,
                        Gtk.PositionType.RIGHT, 2, 10)

    self.online_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    self.scrlwnd_online.add(self.online_box)
    self.online_box.override_background_color(Gtk.StateType.NORMAL, Gdk.RGBA(1, 1, 1, .8))

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

    self.lines = []
    self.old_lines = []
    self.online = []
    self.updating = False
    self.quitting = False
    self.logged = False

    self.update_data()
    self.update_gui()

    self.timer_upd = RepeatedTimer(DELAY, self.update_data)
    GLib.timeout_add(1000, self.update_gui)

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
      request = requests.get(URLGET, headers=HEADERS)
      response = json.loads(request.text)
      for line in reversed(response["Body"]["messages"]):
        self.lines.append({"user": line["user"],
                           "date": line["date"]["full"],
                           "msg": line["text"],
                           "short": line["date"]["short"]})
      request = requests.get(URLONLINE)
      response = json.loads(request.text)
      if response["Body"] is False:
        self.online = []
      else:
        self.online = response["Body"]
      request = requests.get(URLUSER, headers=HEADERS)
      response = json.loads(request.text)
      if response["Body"] is False:
        self.logged = False
      else:
        self.logged = response["Body"]

      self.updating = False

  def update_gui(self, widget=None):
    if self.updating is False:
      self.btn_upd.set_sensitive(True)
      if self.lines != self.old_lines:
        prev = None
        for child in self.chat_box.get_children():
          child.destroy()
        for line in self.lines:
          label_date = Gtk.Label(line["short"])
          tooltip_date = DateTooltip(text=line["date"])
          label_date.set_has_tooltip(True)
          label_date.connect("query-tooltip", tooltip_date)
          prefix = ""
          if line["user"]["is_admin"] is True:
            prefix = "@"
          label_user = Gtk.Label(prefix + line["user"]["name"])
          label_msg = Gtk.Label(line["msg"])
          label_date.set_line_wrap(True)
          label_user.set_line_wrap(True)
          label_msg.set_line_wrap(True)
          label_date.set_justify(Gtk.Justification.LEFT)
          label_user.set_justify(Gtk.Justification.LEFT)
          label_msg.set_justify(Gtk.Justification.LEFT)
          label_date.set_xalign(0)
          label_date.set_yalign(0)
          label_user.set_xalign(0)
          label_user.set_yalign(0)
          label_msg.set_xalign(0)
          label_msg.set_yalign(0)
          label_date.set_selectable(True)
          label_user.set_selectable(True)
          label_msg.set_selectable(True)
          if not prev:
            self.chat_box.add(label_date)
          else:
            self.chat_box.attach_next_to(label_date, prev,
                                         Gtk.PositionType.BOTTOM, 1, 1)
          self.chat_box.attach_next_to(label_user, label_date,
                                       Gtk.PositionType.RIGHT, 1, 1)
          self.chat_box.attach_next_to(label_msg, label_user,
                                       Gtk.PositionType.RIGHT, 1, 1)
          label_date.show()
          label_user.show()
          label_msg.show()
          prev = label_date
        self.old_lines = copy.deepcopy(self.lines)
      for child in self.online_box.get_children():
        child.destroy()
      online_label = Gtk.Label("\t\tOnline:")
      online_label.set_xalign(0)
      online_label.set_yalign(0)
      online_label.set_justify(Gtk.Justification.LEFT)
      self.online_box.add(online_label)
      online_label.show()
      for user in self.online:
        prefix = ""
        if user["is_admin"]:
          prefix = "@"
        label = Gtk.Label(prefix + user["name"])
        label.set_xalign(0)
        label.set_yalign(0)
        label.set_justify(Gtk.Justification.LEFT)
        self.online_box.add(label)
        label.show()
      if self.logged:
        self.btn_send.set_sensitive(True)
        self.entry.show()
      else:
        self.btn_send.set_sensitive(False)
        self.entry.hide()
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
      return False
    return True

  def send_msg_thread(self, msg):
    r = requests.post(URLSEND, headers=HEADERS, data={"text": msg})
    self.sending = False


win = Chat()
win.connect("delete-event", win.bh_quit)
win.show_all()
Gtk.main()

# vim: set expandtab tabstop=2 shiftwidth=2 autoindent:
