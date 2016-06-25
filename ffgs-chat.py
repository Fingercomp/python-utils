#!/usr/bin/env python3

"""
   Copyright 2016 Fingercomp

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

from threading import Thread
from threading import Timer
import urllib.request as ur
import sys
import os.path
import copy
import requests
import json
import time
from html.parser import HTMLParser
from bs4 import BeautifulSoup as Soup

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, GObject

VERSION = "2.2.0"

GLib.threads_init()

home = os.path.expanduser("~") + "/"
config = home + ".local/share/python-utils/"


root = Gtk.Application.new(None, 0)

# CONFIGURATION
if not os.path.exists(config):
    os.makedirs(config, exist_ok=True)

if not os.path.exists(config + "ffgs-chat.cfg"):
    f = open(config + "ffgs-chat.cfg", "w")
    f.write("")
    f.close()
    dialog = Gtk.MessageDialog(parent=Gtk.Window(),
                               message_type=Gtk.MessageType.INFO,
                               buttons=Gtk.ButtonsType.OK,
                               message_format="Configuration file created!")
    dialog.format_secondary_markup("Path to file: <b>" + config +
                                   "ffgs-chat.cfg</b>")
    dialog.run()
    dialog.destroy()

if not os.path.exists(config + "icons/"):
    os.mkdir(config + "icons/")

if not os.path.exists(config + "icons/ffgs-chat-icon.png"):
    response = ur.urlopen(
        "https://raw.githubusercontent.com/Fingercomp/"
        "python-utils/master/icons/ffgs-chat-icon.png")
    f = open(config + "icons/ffgs-chat-icon.png", "wb")
    img = response.read()
    f.write(img)
    f.close()

userdata = [i.strip() for i in open(config + "ffgs-chat.cfg").readlines()]

DELAY = 10
URLGET = "http://ffgs.ru/chat/getmsg?id=1"
URLSEND = "http://ffgs.ru/chat/say"
URLONLINE = "http://ffgs.ru/chat/getonline"
URLUSER = "http://ffgs.ru/chat/getuser"
URLGETKILLERS = "http://api.ffgs.ru/rust/?action=getKillers"
URLGETVICTIMS = "http://api.ffgs.ru/rust/?action=getVictims"
HEADERS = {
    "Cookie": "auth_user=" + userdata[0] + "; auth_hash=" + userdata[1]
}

lt = "\uf8f0"
gt = "\uf8f1"
tags2replace = {
    "strong": "b",
    "em": "i",
}


# http://stackoverflow.com/a/13151299
class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
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


class RustWindow(Gtk.Window):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_default_size(300, 400)

        self.box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        self.box.set_homogeneous(True)

        self.add(self.box)

        self.scrlwnd_killers = Gtk.ScrolledWindow()
        self.scrlwnd_killers.set_vexpand(True)
        self.scrlwnd_killers.set_hexpand(True)
        self.box.add(self.scrlwnd_killers)

        self.scrlwnd_victims = Gtk.ScrolledWindow()
        self.scrlwnd_victims.set_vexpand(True)
        self.scrlwnd_victims.set_hexpand(True)
        self.box.add(self.scrlwnd_victims)

        self.list_killers = Gtk.ListStore(str, str)
        self.list_victims = Gtk.ListStore(str, str)

        self.tree_killers = Gtk.TreeView.new_with_model(self.list_killers)
        for i, title in enumerate(["Player", "Kills"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            self.tree_killers.append_column(column)

        self.tree_victims = Gtk.TreeView.new_with_model(self.list_victims)
        for i, title in enumerate(["Player", "Deaths"]):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=i)
            self.tree_victims.append_column(column)

        self.tree_killers.set_grid_lines(Gtk.TreeViewGridLines.VERTICAL)
        self.tree_victims.set_grid_lines(Gtk.TreeViewGridLines.VERTICAL)

        self.scrlwnd_killers.add(self.tree_killers)
        self.scrlwnd_victims.add(self.tree_victims)

        self.show_all()

        self.connect("delete-event", self.hide_on_delete_handler)

        self.shown = False
        self.quitting = False
        self.updating = False
        self.old_killers = []
        self.old_victims = []
        self.killers = []
        self.victims = []

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
        self.killers = []
        self.victims = []

        try:
            response = requests.get(URLGETKILLERS)
            killers = json.loads(response.text)
            if killers["status"] != "ok" or not killers["body"]:
                raise Exception
            for pair in killers["body"]:
                self.killers.append(pair)
        except:
            e = sys.exc_info()[0]
            print(str(e))
            self.killers = self.old_killers

        try:
            response = requests.get(URLGETVICTIMS)
            victims = json.loads(response.text)
            if victims["status"] != "ok" or not victims["body"]:
                raise Exception
            for pair in victims["body"]:
                self.victims.append(pair)
        except:
            e = sys.exc_info()[0]
            print(str(e))
            self.victims = self.old_victims

        self.updating = False

    def update_gui(self, *args):
        if self.updating:
            return True

        if not self.shown:
            return True

        if self.old_killers != self.killers:
            self.list_killers.clear()
            for i in self.killers:
                self.list_killers.append([i["name"], i["kills"]])

        if self.old_victims != self.victims:
            self.list_victims.clear()
            for i in self.victims:
                self.list_victims.append([i["name"], i["deaths"]])

        return True


class Chat(Gtk.Window):

    def __init__(self):
        super().__init__(title="FFGS chat client [" + VERSION + "]")
        self.set_default_size(500, 200)

        self.timeout_id = None

        grid = Gtk.Grid(column_spacing=5, row_spacing=5,
                        hexpand=True, vexpand=True)
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
        self.scrlwnd_online.set_hexpand(True)
        frame_online.add(self.scrlwnd_online)
        grid.attach_next_to(frame_online, frame_chat,
                            Gtk.PositionType.RIGHT, 2, 9)

        self.online_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                  spacing=5)
        self.scrlwnd_online.add(self.online_box)
        self.online_box.override_background_color(Gtk.StateType.NORMAL,
                                                  Gdk.RGBA(1, 1, 1, .8))

        self.entry = Gtk.Entry()
        self.entry.connect("activate", self.send_msg)
        grid.attach_next_to(self.entry, frame_chat, Gtk.PositionType.BOTTOM,
                            8, 1)

        self.btn_send = Gtk.Button(label=">")
        self.btn_send.connect("clicked", self.send_msg)
        grid.attach_next_to(self.btn_send, self.entry,
                            Gtk.PositionType.RIGHT, 1, 1)

        self.btn_upd = Gtk.Button(label="↻")
        self.btn_upd.connect("clicked", self.bh_update)
        grid.attach_next_to(self.btn_upd, self.btn_send,
                            Gtk.PositionType.RIGHT, 1, 1)

        self.btn_rust = Gtk.Button(label="ⓘ")
        self.btn_rust.connect("clicked", self.toggle_rust_win)
        grid.attach_next_to(self.btn_rust, frame_online,
                            Gtk.PositionType.BOTTOM, 2, 1)

        self.ind = Gtk.StatusIcon.new()
        self.ind.set_from_file(config + "icons/ffgs-chat-icon.png")
        self.ind.connect("activate", self.toggle_visibility)

        self.win_rust = RustWindow(title="Rust stats")
        self.win_rust.set_visible(False)

        self.lines = []
        self.old_lines = []
        self.online = []
        self.updating = False
        self.quitting = False
        self.logged = False
        self.hidden = False
        self.first = True

        self.update_data()
        self.update_gui()

        self.timer_upd = RepeatedTimer(DELAY, self.update_data)
        GLib.timeout_add(1000, self.update_gui)

    def toggle_rust_win(self, *args):
        if not self.win_rust.shown:
            self.win_rust.update_data()
        self.win_rust.set_visible(not self.win_rust.shown)
        self.win_rust.shown = not self.win_rust.shown

    def toggle_visibility(self, widget):
        if self.hidden:
            root.release()
            self.set_visible(True)
            self.win_rust.set_visible(self.win_rust.shown)
        else:
            root.hold()
            self.set_visible(False)
            self.win_rust.set_visible(False)
        self.hidden = not self.hidden
        return True

    def cursor_fix(self, widget, step_type, step, *args):
        if step == 1:
            widget.get_parent().child_focus(Gtk.DirectionType.RIGHT)
        elif step == -1:
            widget.get_parent().child_focus(Gtk.DirectionType.LEFT)

    def paste_nick(self, widget, event):
        if event.button == 1:
            if event.state & Gdk.ModifierType.CONTROL_MASK == 4:
                if self.logged:
                    nickname = widget.get_text()
                    if nickname[:1] != "@":
                        nickname = "@" + nickname
                    self.entry.do_insert_at_cursor(self.entry, nickname + " ")
                    self.entry.grab_focus_without_selecting()
                    move_at = (self.entry.props.cursor_position +
                               len(nickname) + 1)
                    self.entry.do_move_cursor(
                        self.entry,
                        Gtk.MovementStep.LOGICAL_POSITIONS,
                        move_at,
                        False)
        return True

    def bh_quit(self, widget=None, *args):
        self.quitting = True
        while self.updating is True:
            time.sleep(0.05)
        self.timer_upd.cancel()
        self.win_rust.quit_handler()
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
            try:
                request = requests.get(URLGET, headers=HEADERS)
            except:
                self.lines = old_lines
            else:
                response = json.loads(request.text)
                html_parser = HTMLParser()
                for line in reversed(response["Body"]["messages"]):
                    user_short = line["user"]["name"]
                    msg = line["text"]
                    if len(user_short) > 16:
                        user_short = user_short[:16] + "…"
                    for tag in tags2replace:
                        rp_text = tags2replace[tag]
                        msg = msg.replace("<" + tag + ">", lt + rp_text + gt) \
                            .replace("</" + tag + ">", lt + "/" + rp_text + gt)
                    html = Soup(msg, "html.parser")
                    for tag in html.find_all("span", class_="spoiler"):
                        cl = ""
                        style = ""
                        try:
                            cl = tag["class"][0]
                        except:
                            try:
                                style = tag["style"]
                            except:
                                pass
                        if cl == "spoiler":
                            tag.replace_with(
                                lt + 'span foreground="white" background="'
                                'black"' + gt + "[" + tag.string + "]" + lt +
                                "/span" + gt)
                        if style == "text-decoration: underline;":
                            tag.replace_with(lt + "u" + gt + tag.string +
                                             lt + "/u" + gt)
                        elif style == "text-decoration: line-through;":
                            tag.replace_with(lt + "s" + gt + tag.string + lt +
                                             "/s" + gt)
                        elif style == "text-decoration: overline;":
                            tag.replace_with(lt + "s" + gt + tag.string + lt +
                                             "/s" + gt)
                    msg = html_parser.unescape(str(html))
                    msg = msg.replace("<", "&lt;").replace(">", "&gt;")
                    msg = msg.replace(lt, "<").replace(gt, ">")
                    msg = msg.replace("&", "&amp;")
                    self.lines.append({"user": line["user"],
                                       "date": line["date"]["full"],
                                       "msg": msg,
                                       "user_short": user_short,
                                       "short": line["date"]["short"]})
            try:
                request = requests.get(URLONLINE)
            except:
                self.online = old_online
            else:
                response = json.loads(request.text)
                if response["Body"] is False:
                    self.online = []
                else:
                    self.online = response["Body"]
            try:
                request = requests.get(URLUSER, headers=HEADERS)
            except:
                self.logged = False
            else:
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
                    label_user = Gtk.Label()
                    label_user.set_markup(prefix + line["user_short"])
                    tooltip_user = DateTooltip(text=line["user"]["name"] +
                                               " (" + line["user"]["login"] +
                                               ")")
                    label_user.set_has_tooltip(True)
                    label_user.connect("query-tooltip", tooltip_user)
                    label_user.connect("button-press-event", self.paste_nick)
                    label_msg = Gtk.Label()
                    label_msg.set_markup(line["msg"])
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
                    label_date.connect("move-cursor", self.cursor_fix)
                    label_user.connect("move-cursor", self.cursor_fix)
                    label_msg.connect("move-cursor", self.cursor_fix)
                    if not prev:
                        self.chat_box.attach(label_date, 1, 1, 1, 1)
                    else:
                        self.chat_box.attach_next_to(label_date, prev,
                                                     Gtk.PositionType.BOTTOM,
                                                     1, 1)
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
            online_label = Gtk.Label()
            online_label.set_markup("<span foreground=\"gray\">Online</span>")
            online_label.set_xalign(.5)
            online_label.set_yalign(.5)
            online_label.set_justify(Gtk.Justification.CENTER)
            self.online_box.add(online_label)
            online_label.show()
            for user in self.online:
                prefix = ""
                if user["is_admin"]:
                    prefix = "@"
                label = Gtk.Label(prefix + user["name"])
                tooltip = DateTooltip(text=user["login"])
                label.set_has_tooltip(True)
                label.connect("query-tooltip", tooltip)
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
        self.timeout_progress_entry = GObject.timeout_add(
            100,
            self.do_pulse,
            None)
        msg = self.entry.get_text()
        self.thread_send = Thread(target=self.send_msg_thread, args=(msg,))
        self.thread_send.start()
        self.timeout_check_sent = GObject.timeout_add(500, self.check_sent)

    def do_pulse(self, *args):
        self.entry.progress_pulse()
        return True

    def check_sent(self, *args):
        if self.sending is False:
            self.btn_send.set_sensitive(True)
            GObject.source_remove(self.timeout_progress_entry)
            self.timeout_progress_entry = None
            self.entry.set_progress_pulse_step(0)
            self.entry.set_text("")
            self.bh_update()
            return False
        return True

    def send_msg_thread(self, msg):
        try:
            requests.post(URLSEND, headers=HEADERS, data={"text": msg})
        except:
            pass
        self.sending = False


win = Chat()
win.connect("delete-event", win.bh_quit)
win.show_all()
Gtk.main()

# vim: set expandtab tabstop=4 shiftwidth=4 autoindent:
