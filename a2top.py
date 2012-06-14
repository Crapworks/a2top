#!/usr/bin/python

import curses
import sys
import re
import os

from signal import signal, SIGINT
from optparse import OptionParser
from time import sleep
from datetime import timedelta
from urllib2 import urlopen

class ApacheStatus(object):
    scoreboard = {}
    infos = {}

    mapping = {
        "_":"Waiting for Connection",
        "S":"Starting up",
        "R":"Reading Request",
        "W":"Sending Reply",
        "K":"Keepalive (read)",
        "D":"DNS Lookup",
        "C":"Closing connection",
        "L":"Logging",
        "G":"Gracefully finishing",
        "I":"Idle cleanup of worker",
        ".":"Open slot with no current process",
    }

    info_keys = [
        'Total Accesses',
        'Total kBytes',
        'Uptime',
        'ReqPerSec',
        'BytesPerSec',
        'BytesPerReq',
        'BusyWorkers',
        'IdleWorkers',
        'Scoreboard',
        'CPULoad'
    ]

    def __init__(self, host):
        self.host = host
        self.regexes = [ re.compile('%s: (?P<%s>.*)' % (key, key.replace(' ', '_'))) for key in self.info_keys ]

    def convert_bytes(self, bytes):
        if bytes >= 1099511627776:
            return '%.2fT' % (bytes / 1099511627776, ) 
        elif bytes >= 1073741824:
            return '%.2fG' % (bytes / 1073741824, )
        elif bytes >= 1048576:
            return '%.2fM' % (bytes / 1048576, )
        elif bytes >= 1024:
            return '%.2fK' % (bytes / 1024, )
        else:
            return '%.2fb' % bytes

    def update(self):
        try:
            con = urlopen("%s" % (self.host), timeout=1)
        except:
            return None

        data = con.read()

        results = [ regex.search(data) for regex in self.regexes ]
        for result in results:
            if result:
                self.infos.update(result.groupdict())

        self.scoreboard.update(self.parse_scoreboard(self.infos['Scoreboard']))
        del self.infos['Scoreboard']

        # beautify
        if 'Uptime' in self.infos.keys():
            self.infos['Uptime'] = timedelta(seconds=int(self.infos['Uptime']))

        if 'Total_kBytes' in self.infos.keys():
            self.infos['Total_kBytes'] = self.convert_bytes(float(self.infos['Total_kBytes']) * 1024)          

        if 'BytesPerSec' in self.infos.keys():
            self.infos['BytesPerSec'] = self.convert_bytes(float(self.infos['BytesPerSec']))          

        if 'BytesPerReq' in self.infos.keys():
            self.infos['BytesPerReq'] = self.convert_bytes(float(self.infos['BytesPerReq']))          

    def parse_scoreboard(self, sb):
        scoreboard = {
            "Waiting for Connection":0,
            "Starting up":0,
            "Reading Request":0,
            "Sending Reply":0,
            "Keepalive (read)":0,
            "DNS Lookup":0,
            "Closing connection":0,
            "Logging":0,
            "Gracefully finishing":0,
            "Idle cleanup of worker":0,
            "Open slot with no current process":0,
        }

        for item in sb:
            scoreboard[self.mapping[item]] += 1

        return scoreboard

class ApacheTop(object):
    def __init__(self, hosts = ['http://localhost/server-status?auto'], interval = 1):
        self.hosts = hosts
        self.interval = interval

        # fix curses / readline bug during window resize
        os.unsetenv('LINES')
        os.unsetenv('COLUMNS')

        self.a2stat = [ ApacheStatus(host) for host in self.hosts ]
        self.scr = curses.initscr()
        self.scr.nodelay(1)

        curses.start_color()
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)

        signal(SIGINT, self.cleanup)
        self.exit = False

    def run(self):
        offset = 4
        self.scr.addstr(2, 7, "[ Scoreboard ]", curses.color_pair(1) | curses.A_BOLD)
        self.scr.addstr(2, 97, "[ Server Status ]", curses.color_pair(1) | curses.A_BOLD)

        while not self.exit:
            c = self.scr.getch()
            if c == ord('q'): break
            if c == curses.KEY_RESIZE: self.scr.refresh()

            next_host = line = 0
            for stat in self.a2stat:
                line = next_host
                try:
                    self.scr.addstr(line + offset, 7, "[ %s ] (updating...)" % (stat.host, ), curses.color_pair(4) | curses.A_BOLD)
                    stat.update()

                    self.scr.addstr(line + offset, 7, "[ %s ]              " % (stat.host, ), curses.color_pair(4) | curses.A_BOLD)

                    for num, item in enumerate(stat.scoreboard.keys()):
                        self.scr.addstr(line + offset + num + 2, 10, "%-40s : %-10s" % (item, stat.scoreboard[item]))
                        next_host = line + offset + num + 2

                    for num, item in enumerate(stat.infos.keys()):
                        self.scr.addstr(line + offset + num + 2, 100, "%-40s : %-10s" % (item, stat.infos[item]))
                except:
                    pass

            self.scr.refresh()                
            sleep(self.interval)

        self.cleanup(None, None)

    def cleanup(self, signum, frame):
        curses.nocbreak(); 
        self.scr.keypad(0); 
        curses.echo()
        curses.endwin()
        self.exit = True

def main():
    parser = OptionParser(usage="usage: %s [options] http://host1/server-status?auto http://host2/server-status?auto ..." % (sys.argv[0], ))
    parser.add_option("-i", "--interval", action="store", type="int", dest="interval", default=1, help="interval for updateing server infos")
    (options, args) = parser.parse_args(sys.argv[1:])

    a2top = ApacheTop(hosts=args, interval=options.interval)
    a2top.run()

if __name__ == '__main__':
    main()
