#!/usr/bin/env python3

VERSION = "2.0.0"

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
  f = open(config + "cc-chat.cfg", "w")
  f.write("")
  f.close()
  dialog = Gtk.MessageDialog(parent=Gtk.Window(),
                             message_type=Gtk.MessageType.INFO,
                             buttons=Gtk.ButtonsType.OK,
                             message_format="Configuration file created!")
  dialog.format_secondary_markup("Path to file: <b>" + config + \
    "cc-chat.cfg</b>.")
  dialog.run()
  dialog.destroy()

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

if len(userdata) != 2:
  mpl = "s"
  if len(userdata) == 1:
    mpl = ""
  dialog = Gtk.MessageDialog(parent=Gtk.Window(),
                             message_type=Gtk.MessageType.ERROR,
                             buttons=Gtk.ButtonsType.CLOSE,
                             message_format="Bad config!")
  dialog.format_secondary_markup("Got " + str(len(userdata)) + " line" + \
    mpl + ", expected 2")
  dialog.run()
  dialog.destroy()
  sys.exit(-1)

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
URLUSER = "http://computercraft.ru/user/"
URLTOPMONTH = "http://launcher.computercraft.ru/api/topmonth/100"
URLTOPMONEY = "http://launcher.computercraft.ru/api/topmoney/100"
URLTOPUU = "http://launcher.computercraft.ru/api/top/100"
URLINFO = "http://launcher.computercraft.ru/api/info/"
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


class InfoWindow(Gtk.Window):
  
  def __init__(self, nickname = "Byte", *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.set_default_size(300, 480)
    
    self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
    self.main_box.set_homogeneous(False)

    self.grid = Gtk.Grid(column_spacing=5, row_spacing=5, hexpand=True, vexpand=True)
    self.grid.set_border_width(5)
    self.grid.set_column_homogeneous(True)

    self.add(self.main_box)
    self.main_box.add(self.grid)

    self.footer = Gtk.Grid(column_spacing=5, row_spacing=5, hexpand=True)
    self.footer.set_border_width(5)
    self.footer.set_column_homogeneous(True)
    self.main_box.add(self.footer)



    self.nick_label = Gtk.Label(nickname)
    self.nick_label.modify_font(Pango.FontDescription("Bold 20"))
    self.grid.attach(self.nick_label, 1, 1, 1, 1)

    self.balance = Gtk.Label("$ 0")
    self.balance.modify_font(Pango.FontDescription("Bold 14"))
    self.grid.attach_next_to(self.balance, self.nick_label, Gtk.PositionType.RIGHT, 1, 1)

    self.uu = Gtk.Label("UU 0")
    self.uu.modify_font(Pango.FontDescription("Bold 14"))
    self.grid.attach_next_to(self.uu, self.balance, Gtk.PositionType.RIGHT, 1, 1)


    self.month_label = Gtk.Label("Month: #1")
    self.grid.attach_next_to(self.month_label, self.nick_label, Gtk.PositionType.BOTTOM, 1, 1)

    self.money_label = Gtk.Label("Money: #1")
    self.grid.attach_next_to(self.money_label, self.month_label, Gtk.PositionType.RIGHT, 1, 1)

    self.uu_label = Gtk.Label("UU: #1")
    self.grid.attach_next_to(self.uu_label, self.money_label, Gtk.PositionType.RIGHT, 1, 1)


    self.scrlwnd_month = Gtk.ScrolledWindow()
    self.scrlwnd_month.set_vexpand(True)
    self.scrlwnd_month.set_hexpand(True)
    self.grid.attach_next_to(self.scrlwnd_month, self.month_label, Gtk.PositionType.BOTTOM, 1, 1)

    self.scrlwnd_money = Gtk.ScrolledWindow()
    self.scrlwnd_money.set_vexpand(True)
    self.scrlwnd_money.set_hexpand(True)
    self.grid.attach_next_to(self.scrlwnd_money, self.scrlwnd_month, Gtk.PositionType.RIGHT, 1, 1)

    self.scrlwnd_uu = Gtk.ScrolledWindow()
    self.scrlwnd_uu.set_vexpand(True)
    self.scrlwnd_uu.set_hexpand(True)
    self.grid.attach_next_to(self.scrlwnd_uu, self.scrlwnd_money, Gtk.PositionType.RIGHT, 1, 1)


    self.month_list = Gtk.ListStore(str, str, str)
    self.money_list = Gtk.ListStore(str, str, str)
    self.uu_list = Gtk.ListStore(str, str, str, str, str)

    self.month_tree = Gtk.TreeView.new_with_model(self.month_list)
    for i, title in enumerate(["#", "User", "Votes"]):
      renderer = Gtk.CellRendererText()
      column = Gtk.TreeViewColumn(title, renderer, text=i)
      self.month_tree.append_column(column)

    self.money_tree = Gtk.TreeView.new_with_model(self.money_list)
    for i, title in enumerate(["#", "User", "Money"]):
      renderer = Gtk.CellRendererText()
      column = Gtk.TreeViewColumn(title, renderer, text=i)
      self.money_tree.append_column(column)

    self.uu_tree = Gtk.TreeView.new_with_model(self.uu_list)
    for i, title in enumerate(["#", "User", "Votes", "Money", "UU"]):
      renderer = Gtk.CellRendererText()
      column = Gtk.TreeViewColumn(title, renderer, text=i)
      self.uu_tree.append_column(column)

    self.scrlwnd_month.add(self.month_tree)
    self.scrlwnd_money.add(self.money_tree)
    self.scrlwnd_uu.add(self.uu_tree)


    self.votes_label = Gtk.Label()
    self.votes_label.set_markup("<b><i>VOTES</i></b>")
    self.votes_label.set_justify(Gtk.Justification.LEFT)
    self.votes_label.set_xalign(0)
    self.footer.attach(self.votes_label, 1, 1, 1, 1)

    self.mcrate = Gtk.Label()
    self.mcrate.set_markup("<b>MCRate</b>: 0")
    self.footer.attach_next_to(self.mcrate, self.votes_label, Gtk.PositionType.RIGHT, 1, 1)

    self.topcraft = Gtk.Label()
    self.topcraft.set_markup("<b>TopCraft</b>: 0")
    self.footer.attach_next_to(self.topcraft, self.mcrate, Gtk.PositionType.RIGHT, 1, 1)

    self.monitor = Gtk.Label()
    self.monitor.set_markup("<b>MonitorMC</b>: 0")
    self.footer.attach_next_to(self.monitor, self.topcraft, Gtk.PositionType.RIGHT, 1, 1)

    self.show_all()

    self.connect("delete-event", self.hide_on_delete_handler)
    
    self.shown = False
    self.quitting = False
    self.updating = False
    self.nickname = nickname
    self.old_top_month = []
    self.old_top_money = []
    self.old_top_uu = []
    self.old_account = {}
    self.top_month = []
    self.top_money = []
    self.top_uu = []
    self.account = {"money": 0, "uu": 0, "votes": {"rate": 0, "top": 0, "mon": 0}, "tops": {"month": 1, "money": 1, "uu": 1}}

    self.update_data()
    self.update_gui()

    self.timer_upd = RepeatedTimer(30, self.update_data)
    GLib.timeout_add(1000, self.update_gui)

  def quit_handler(self, *args):
    self.quitting = True
    while self.updating:
      time.sleep(.05)
    self.timer_upd.cancel()
    self.destroy()

  def hide_on_delete_handler(self, *args):
    self.hide_on_delete()
    self.shown = False
    return True

  def update_data(self, *args):
    if self.quitting:
      return False
    self.updating = True
    self.top_month = []
    self.top_money = []
    self.top_uu = []
    user_tops = {"month": 1, "money": 1, "uu": 1}
    try:
      response = requests.get(URLTOPMONTH)
      top_month = json.loads(response.text)
      for i, val in enumerate(top_month):
        i += 1
        if val["user"] == self.nickname.lower():
          user_tops["month"] = str(i)
        self.top_month.append({"num": str(i), "user": val["user"], "votes": val["voices"]})
    except:
      self.top_month = self.old_top_month
    
    try:
      response = requests.get(URLTOPMONEY)
      top_money = json.loads(response.text)
      for i, val in enumerate(top_money):
        i += 1
        if val["name"] == self.nickname.lower():
          user_tops["money"] = str(i)
        self.top_money.append({"num": str(i), "user": str(val["name"]), "money": str(val["money"])})
    except:
      self.top_money = self.old_top_money

    try:
      response = requests.get(URLTOPUU)
      top_uu = json.loads(response.text)
      for i, val in enumerate(top_uu):
        i += 1
        if val["name"] == self.nickname.lower():
          user_tops["uu"] = str(i)
        self.top_uu.append({"num": str(i), "user": str(val["name"]), "votes": str(val["voices"]), "uu": str(val["uu"]), "money": str(val["money"])})
    except:
      self.top_uu = self.old_top_uu

    try:
      response = requests.get(URLINFO + self.nickname)
      info = json.loads(response.text)[0]
      self.account = {"money": str(info["money"]), "uu": str(info["uu"]), "votes": {"rate": str(info["votes_mcrate"]), "top": str(info["votes_top"]), "mon": str(info["votes_monit"])}, "tops": user_tops}
    except:
      self.account = self.old_account
    self.updating = False

  def update_gui(self, *args):
    if self.updating:
      return True

    if self.old_top_month != self.top_month:
      self.month_list.clear()
      for i in self.top_month:
        self.month_list.append([i["num"], i["user"], i["votes"]])

    if self.old_top_money != self.top_money:
      self.money_list.clear()
      for i in self.top_money:
        self.money_list.append([i["num"], i["user"], i["money"]])

    if self.old_top_uu != self.top_uu:
      self.uu_list.clear()
      for i in self.top_uu:
        self.uu_list.append([i["num"], i["user"], i["votes"], i["money"], i["uu"]])

    if self.old_account != self.account:
      self.balance.set_text("$ " + self.account["money"])
      self.uu.set_text("UU " + self.account["uu"])
  
      self.mcrate.set_markup("<b>MCRate</b>: " + self.account["votes"]["rate"])
      self.topcraft.set_markup("<b>TopCraft</b>: " + self.account["votes"]["top"])
      self.monitor.set_markup("<b>MonitorMC</b>: " + self.account["votes"]["mon"])
  
      self.month_label.set_text("Month: #" + str(self.account["tops"]["month"]))
      self.money_label.set_text("Money: #" + str(self.account["tops"]["money"]))
      self.uu_label.set_text("UU: #" + str(self.account["tops"]["uu"]))

    self.old_top_month = copy.deepcopy(self.top_month)
    self.old_top_money = copy.deepcopy(self.top_money)
    self.old_top_uu = copy.deepcopy(self.top_uu)
    self.old_account = copy.deepcopy(self.account)

    return True


class Chat(Gtk.Window):
  
  def __init__(self):
    super().__init__(title="CC.ru chat client [" + VERSION + "]")
    self.set_default_size(600, 500)
    self.set_default_icon_from_file(config + "icons/cc-chat-icon.png")

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
    grid.attach(frame_chat, 1, 1, 8, 12)

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
                        Gtk.PositionType.RIGHT, 2, 11)

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

    self.btn_info = Gtk.Button(label="ⓘ")
    self.btn_info.connect("clicked", self.toggle_info_win)
    grid.attach_next_to(self.btn_info, frame_online, Gtk.PositionType.BOTTOM, 2, 1)

    self.ind = Gtk.StatusIcon.new()
    self.ind.set_from_file(config + "icons/cc-chat-icon.png")
    self.ind.connect("activate", self.toggle_visibility)

    self.show_all()

    self.info_win = InfoWindow(nickname = self.get_cur_user())
    self.info_win.set_visible(False)

    self.hidden = False
    self.lines = []
    self.old_lines = []
    self.online = []
    self.user_links = {}
    self.updating = False
    self.quitting = False
    self.first = True

    self.update_data()
    self.update_gui()

    self.timer_upd = RepeatedTimer(DELAY, self.update_data)
    GLib.timeout_add(1000, self.update_gui)

  def toggle_info_win(self, *args):
     self.info_win.set_visible(not self.info_win.shown)
     self.info_win.shown = not self.info_win.shown

  def toggle_visibility(self, widget):
    if self.hidden:
      root.release()
      self.set_visible(True)
      self.entry.grab_focus()
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
    self.info_win.quit_handler()
    Gtk.main_quit()

  def update_data(self, widget=None):
    if self.quitting is True:
      return False
    if self.updating is False:
      self.updating = True
      old_lines = copy.deepcopy(self.lines)
      old_online = copy.deepcopy(self.online)
      self.lines = []
      self.online = []
      request = ur.Request(URL, headers=HEADERS)
      try:
        response = ur.urlopen(request)
      except:
        self.lines = old_lines
      else:
        response = response.read()
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
            title = tag["title"]
            if not title:
              title = ""
            tag.replace_with(lt + "a href=\"" + tag["href"] + "\" title=\"" + \
              title + "\"" + gt + tag.text + lt + "/a" + gt)

          for tag in raw_msg.find_all("strong"):
            tag.replace_with(lt + "b" + gt + tag.text + lt + "/b" + gt)

          for tag in raw_msg.find_all("em"):
            tag.replace_with(lt + "i" + gt + tag.text + lt + "/i" + gt)

          for tag in raw_msg.find_all("span", style="color: black; " + \
            "font-family: courier; background-color: #EAEAEA"):
            tag.replace_with(lt + "span background=\"gray\" " + \
              "foreground=\"white\"" + gt + tag.text + lt + "/span" + gt)

          for tag in raw_msg.find_all("del"):
            tag.replace_with(lt + "s" + gt + tag.text + lt + "/s" + gt)
    
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
      try:
        response = json.loads(ur.urlopen(request).read().decode("utf-8"))
      except:
        self.online = old_online
      else:
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
      if self.first:
        self.entry.grab_focus()
        self.first = False
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
    try:
      r = requests.post(URLSEND, headers=headers, data={"shout": post_data})
    except:
      pass
    self.sending = False

  def get_user(self, uid):
    response = requests.get(URLUSER + uid + "-getuser", headers=HEADERS)
    html = Soup(response.text)
    title = html.find("title").string
    if title.split(" ")[0] == "Ошибка":
      return ""
    return response.url.split("-")[1].replace("/", "")

  def get_cur_user(self):
    options_list = [i.strip() for i in HEADERS["Cookie"].split(";")]
    options = {}
    for i in options_list:
      options[i.split("=")[0]] = "=".join(i.split("=")[1:])

    uid = options["member_id"]
    return self.get_user(uid)


win = Chat()
win.connect("delete-event", win.bh_quit)
Gtk.main()

# vim: set autoindent tabstop=2 shiftwidth=2 expandtab:
