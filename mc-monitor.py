#!/usr/bin/env python3
# -*- coding: utf8 -*-

# VERSION: 1.2.2

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

from mcstatus import MinecraftServer
import time
# import datetime as dt
from threading import Thread
from threading import Timer
import os
import urllib as ur

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from gi.repository import GLib
gi.require_version("Notify", "0.7")

GLib.threads_init()

home = os.path.expanduser("~") + "/"
config = home + ".local/share/python-utils/"

# CONFIGURATION
if not os.path.exists(config):
    os.makedirs(config)

if not os.path.exists(config + "mc-monitor/"):
    os.mkdir(config + "mc-monitor/")

if not os.path.exists(config + "mc-monitor/mc-monitor.cfg"):
    f = open(config + "mc-monitor/mc-monitor.cfg", "w")
    f.write("")
    f.close()
    dialog = Gtk.MessageDialog(parent=Gtk.Window(),
                               message_type=Gtk.MessageType.INFO,
                               buttons=Gtk.ButtonsType.OK,
                               message_format="Configuration file created!")
    dialog.format_secondary_markup(
        "Path to file: <b>" + config + "mc-monitor/mc-monitor.cfg</b>.")
    dialog.run()
    dialog.destroy()

# if not os.path.exists(config + "mc-monitor/vote"):
#     f = open(config + "mc-monitor/vote", "w")
#     f.write("2012 12 12 12 12 12")

if not os.path.exists(config + "icons/"):
    os.mkdir(config + "icons/")

if not os.path.exists(config + "icons/mc-monitor.png"):
    response = ur.urlopen("https://raw.githubusercontent.com/Fingercomp/"
                          "python-utils/master/icons/mc-monitor.png")
    f = open(config + "icons/mc-monitor.png", "wb")
    img = response.read()
    f.write(img)
    f.close()

# if not os.path.exists(config + "icons/mc-monitor-important.png"):
#     response = ur.urlopen("https://raw.githubusercontent.com/Fingercomp/" \
#         "python-utils/master/icons/mc-monitor-important.png")
#     f = open(config + "icons/mc-monitor-important.png", "wb")
#     img = response.read()
#     f.write(img)
#     f.close()

DELAY = 15
# VOTEFILE = config + "mc-monitor/vote"
SERVERSFILE = config + "mc-monitor/mc-monitor.cfg"

# nots = True

# if os.name == "nt":
#     # Windows, turn off notifications
#     nots = False

# if nots:
#     from gi.repository import Notify


# http://stackoverflow.com/a/13151299
class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._time = None
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


class CheckServers:
    def __init__(self):
        self.ind = Gtk.StatusIcon.new_from_file(
            config + "icons/mc-monitor.png")
        self.ind.set_tooltip_text("...")

        self.servers = {}
        conf = open(SERVERSFILE, "r")
        for line in reversed(conf.readlines()):
            line = line.strip()
            # print(line)
            data = line.split("=")
            self.servers[data[0]] = [None, None, data[1]]
        conf.close()

        self.menu_setup()
        self.ind.connect("popup-menu", lambda icon, btn, time: self.menu.popup(
            None, None, None, None, btn, time))
#         if nots is True:
#             Notify.init("check-servers")
#             self.notification = Notify.Notification.new(
#                 "Vote?", "It's time to vote!")
#             self.min30_sent = False
#             self.min15_sent = False
#             self.min5_sent = False
#             self.min1_sent = False
#         self.show_notification = False
        self.ready_to_show = True
        self.gui_upd = False
#         self.cur_icon = 0

    def menu_setup(self):
        self.menu = Gtk.Menu()

        for addr in self.servers:
            cws = self.servers[addr]
            cws[1] = Gtk.Menu()
            cws[0] = Gtk.MenuItem(cws[2])
            cws[0].set_submenu(cws[1])
            cws[0].show()
            self.menu.append(cws[0])


#        self.separator_vote = Gtk.SeparatorMenuItem()
#        self.separator_vote.show()
#        self.menu.append(self.separator_vote)

#        self.vote_item = Gtk.MenuItem("Loading...")
#        self.vote_item.connect("activate", self.rewrite_date)
#        self.vote_item.show()
#        self.menu.append(self.vote_item)

        self.separator_controls = Gtk.SeparatorMenuItem()
        self.separator_controls.show()
        self.menu.append(self.separator_controls)

        self.refresh_item = Gtk.MenuItem("Refresh")
        self.refresh_item.connect("activate", self.spawn_upddata_thread)
        self.refresh_item.show()
        self.menu.append(self.refresh_item)

        self.quit_item = Gtk.MenuItem("Quit")
        self.quit_item.connect("activate", self.quit)
        self.quit_item.show()
        self.menu.append(self.quit_item)

    def main(self):
        self.update_data()
        self.update()
        self.upddata_timer = RepeatedTimer(DELAY, self.update_data)
        self.upddata_timer.start()
        GLib.timeout_add(1000, self.update)
#        GLib.timeout_add(1000, self.update_vote)
        Gtk.main()

    def spawn_upddata_thread(self, widget=True):
        self.upddata_thread = Thread(target=self.update_data)
        self.upddata_thread.start()

    def quit(self, widget=True):
        self.upddata_timer.cancel()
#        if nots:
#            Notify.uninit()
        Gtk.main_quit()

#    def Notify_vote(self):
#        if self.show_notification is True and nots is True:
#            self.notification.show()
#            return True
#        return False

#    def rewrite_date(self, widget=True):
#        cur_time = dt.datetime.now()
#        open(VOTEFILE, "w").write((cur_time + dt.timedelta(days=1)).strftime(
#            "%Y %m %d %H %M %S"))

#    def update_vote(self):
#        vote_at = dt.datetime(*[int(i) for i in open(VOTEFILE).read().strip()
#                                .split(" ")])
#        cur_time = dt.datetime.now()
#        if cur_time >= vote_at:
#            self.vote_item.set_sensitive(True)
#            if self.cur_icon != 1:
#                self.ind.set_from_file(
#                    config + "icons/mc-monitor-important.png")
#                self.cur_icon = 1
#            self.vote_item.set_label("Restart the timer")
#            if self.show_notification is False and nots is True:
#                self.show_notification = True
#                self.notification.show()
#                GLib.timeout_add(30000, self.Notify_vote)
#        else:
#            if self.cur_icon != 0:
#                self.ind.set_from_file(config + "icons/mc-monitor.png")
#                self.cur_icon = 0
#            vote_delta = vote_at - cur_time
#            self.vote_item.set_label("Next vote: " + str(vote_delta)
#                .split(".")[0])
#            self.vote_item.set_sensitive(False)
#            self.show_notification = False
#            if nots is True:
#                if vote_delta.seconds < 40:
#                    # Reset values to Notify again next time
#                    self.min30_sent = False
#                    self.min15_sent = False
#                    self.min5_sent = False
#                    self.min1_sent = False
#                elif vote_delta.seconds > 55 and vote_delta.seconds < 60 and
#                        self.min1_sent is False:
#                    # Send a notification: 1 minute
#                    Notify.Notification.new("Prepare to vote",
#                                            "1 minute left!").show()
#                    self.min30_sent = True
#                    self.min15_sent = True
#                    self.min5_sent = True
#                    self.min1_sent = True
#                elif vote_delta.seconds > 295 and
#                        vote_delta.seconds < 300 and
#                        self.min5_sent is False:
#                    # Send a notification: 5 minutes
#                    Notify.Notification.new("Prepare to vote",
#                                            "5 minutes left!").show()
#                    self.min30_sent = True
#                    self.min15_sent = True
#                    self.min5_sent = True
#                elif vote_delta.seconds > 895 and vote_delta.seconds < 900 and
#                        self.min15_sent is False:
#                    # Send a notification: 15 minutes
#                    Notify.Notification.new("Prepare to vote",
#                                            "15 minutes left!").show()
#                    self.min30_sent = True
#                    self.min15_sent = True
#                elif vote_delta.seconds > 1795 and
#                        vote_delta.seconds < 1800 and
#                        self.min30_sent is False:
#                    # Send a notification: 30 minutes
#                    Notify.Notification.new("Prepare to vote",
#                                            "30 minutes left!").show()
#                    self.min30_sent = True
#        return True

    def update_data(self):
        if self.ready_to_show is True:
            while self.gui_upd is True:
                time.sleep(0.01)
            self.ready_to_show = False
            self.servdata = {}
            self.totalservdata = {"online": 0, "max": 0}
            for addr in self.servers:
                # print("Upd: " + addr)
                self.servdata[addr] = {
                    "online": 0,
                    "max": 0,
                    "latency": 0,
                    "soft": "",
                    "query": False,
                    "ison": False,
                    "players": []
                }
                try:
                    server = MinecraftServer.lookup(addr)
                    status = server.status()
                    try:
                        query = server.query()
                        self.servdata[addr] = {
                            "online": status.players.online,
                            "max": status.players.max,
                            "latency": status.latency,
                            "soft": query.software.version,
                            "query": True,
                            "ison": True,
                            "players": [pl for pl in query.players.names]
                        }
                    except:
                        self.servdata[addr] = {
                            "online": status.players.online,
                            "max": status.players.max,
                            "latency": status.latency,
                            "soft": "",
                            "query": False,
                            "ison": True,
                            "players": []
                        }
                    finally:
                        self.totalservdata["online"] += status.players.online
                        self.totalservdata["max"] += status.players.max
                except:
                    # Server is offline =\
                    self.servdata[addr] = {
                        "online": 0,
                        "max": 0,
                        "latency": 0,
                        "soft": "",
                        "query": False,
                        "ison": False,
                        "players": []
                    }
                # print("Data [" + addr + "]:", self.servdata[addr])
            self.ready_to_show = True
            return True

    def update(self, widget=True):
        if self.ready_to_show is True:
            self.gui_upd = True
            self.refresh_item.set_label("Refresh")
            self.refresh_item.set_sensitive(True)
            for addr in self.servdata:
                # print("GUI: " + addr)
                cws = self.servers[addr]
                info = self.servdata[addr]
                for item in cws[1]:
                    cws[1].remove(item)
                cws[0].set_sensitive(True)
                if info["query"] is True:
                    cws[0].set_label(cws[2] + ": {0}/{1}, {2} ms, MC: {3}"
                                     .format(info["online"], info["max"],
                                             info["latency"], info["soft"]))
                    if len(info["players"]) > 0:
                        for i in info["players"]:
                            cur_menu_item = Gtk.MenuItem(i)
                            cur_menu_item.set_sensitive(False)
                            cur_menu_item.show()
                            cws[1].append(cur_menu_item)
                    else:
                        cws[0].set_sensitive(False)
                elif info["ison"] is True:
                    cws[0].set_label(cws[2] + " [Q̶]: {0}/{1}, {2} ms".format(
                        info["online"], info["max"], info["latency"]))
                    cws[0].set_sensitive(False)
                if info["ison"] is False:
                    cws[0].set_label(cws[2] + ": Info not available")
                    cws[0].set_sensitive(False)
            # print("Max: " + str(self.totalservdata["max"]))
            if self.totalservdata["max"] == 0:
                self.ind.set_tooltip_text("OFF")
            else:
                self.ind.set_tooltip_text(str(
                    self.totalservdata["online"]) + "/" +
                    str(self.totalservdata["max"]))
            self.gui_upd = False
        else:
            self.refresh_item.set_label("Refreshing...")
            self.refresh_item.set_sensitive(False)
        return True

if __name__ == "__main__":
    indicator = CheckServers()
    indicator.main()

# vim: autoindent tabstop=4 shiftwidth=4 expandtab:
