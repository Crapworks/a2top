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

class ApacheTopModule(object):
    def __init__(self, scr):
        self.scr = scr
        self.last_draw = {}

    def draw_header(self, stats):
        pass

    def draw_updateing(self, stats, id):
        pass    

    def draw(self, stats, id):
        pass
        
class ApacheTopWidescreen(ApacheTopModule):
    def draw_header(self):
        self.offset = 4
        self.scr.addstr(2, 7, "[ Scoreboard ]", curses.color_pair(1) | curses.A_BOLD)
        self.scr.addstr(2, 97, "[ Server Status ]", curses.color_pair(1) | curses.A_BOLD)
    
    def draw_updateing(self, stats, id):
        if not (id - 1) in self.last_draw.keys():
            line = 0
        else:
            line = self.last_draw[(id - 1)]
            
        self.scr.addstr(line + self.offset, 7, "[ %s ] (updating...)" % (stats.host, ), curses.color_pair(4) | curses.A_BOLD)
    
    def draw(self, stats, id):
        if not (id - 1) in self.last_draw.keys():
            line = 0
        else:
            line = self.last_draw[(id - 1)]
            
        self.scr.addstr(line + self.offset, 7, "[ %s ]              " % (stats.host, ), curses.color_pair(4) | curses.A_BOLD)

        # draw scoreboard stats
        for num, item in enumerate(stats.scoreboard.keys()):
            self.scr.addstr(line + self.offset + num + 2, 10, "%-40s : %-10s" % (item, stats.scoreboard[item]))
            line_tmp = line + self.offset + num + 2

        # draw (extended) infos
        for num, item in enumerate(stats.infos.keys()):
            self.scr.addstr(line + self.offset + num + 2, 100, "%-40s : %-10s" % (item, stats.infos[item]))

        # draw worker graph
        self.scr.addstr(line_tmp, 100, "[ ", curses.A_BOLD)

        total_worker = sum(map(int, stats.scoreboard.values()))
        unused_worker = int(stats.scoreboard['Open slot with no current process'])                    
        prozent_free  = int((float(unused_worker) / float(total_worker)) * 100)

        # draw used slots
        self.scr.addstr(line_tmp, 102, "|" * (100 - prozent_free), curses.color_pair(3) | curses.A_BOLD)

        # draw free slots
        self.scr.addstr(line_tmp, 102 + (100 - prozent_free), "|" * prozent_free, curses.color_pair(2) | curses.A_BOLD)

        self.scr.addstr(line_tmp, 202, " ]", curses.A_BOLD)
        
        self.last_draw[id] = line_tmp
    

class ApacheTopTabular(ApacheTopModule):
    def draw_header(self):
        self.top_padding = 3
        self.left_padding = 3
        self.col_width = 20
        self.line = 1
        self.last_width = {}
        
    def draw_updateing(self, stats, id):
        pass
        
    def draw(self, stats, id):
        if not (id - 1) in self.last_width.keys():
            width = 0
        else:
            width = self.last_width[(id - 1)]
        
        if id == 0:
            self.last_width = {}
            self.line = 1
            self.break_id = 0
    
        datasources = {}
        datasources.update(stats.scoreboard)
        datasources.update(stats.infos)
        
        sources_max_width = len(max(datasources.keys(), key=len)) + 2
        sources_num_lines = len(datasources.keys())
        
        y, x = self.scr.getmaxyx()        
        
        if x < ((width + 40) / self.line):
            self.line += 1     
            self.break_id = id
        
        self.scr.addstr(self.top_padding - 2 + (sources_num_lines * (self.line -1) + (5 * (self.line-1))), self.left_padding + width - ((self.col_width * self.break_id) * (self.line - 1)) + sources_max_width, "%-20s" % (stats.host.split('/')[2].split('.')[0], ) , curses.color_pair(2) | curses.A_BOLD)
        for num, datasource in enumerate(datasources.keys()):
            self.scr.addstr(num + self.top_padding + (sources_num_lines * (self.line -1) + (5 * (self.line-1))),  self.left_padding, "%s%s" % (datasource, " " * (sources_max_width - len(datasource))) , curses.color_pair(1) | curses.A_BOLD) 
            self.scr.addstr(num + self.top_padding + (sources_num_lines * (self.line -1) + (5 * (self.line-1))),  self.left_padding + width - ((self.col_width * self.break_id) * (self.line - 1)) + sources_max_width, "%-20s" % (datasources[datasource], ) , curses.A_BOLD)
        
        self.last_width[id] = width + self.col_width

class ApacheTop(object):
    def __init__(self, hosts = ['http://localhost/server-status?auto'], mode = ApacheTopWidescreen, interval = 1):
        self.hosts = hosts
        self.interval = interval
        self.modes = [ApacheTopTabular, ApacheTopWidescreen]
        self.itermodes = iter(self.modes)
        
        # fix curses / readline bug during window resize
        os.unsetenv('LINES')
        os.unsetenv('COLUMNS')

        self.a2stat = [ ApacheStatus(host) for host in self.hosts ]        
        self.scr = curses.initscr()
        self.scr.nodelay(1)
        
        self.mode = mode(self.scr)

        curses.start_color()
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)

        signal(SIGINT, self.cleanup)
        self.exit = False

    def run(self):
        self.mode.draw_header()

        while not self.exit:
            c = self.scr.getch()
            if c == ord('q'): break            
            if c == curses.KEY_RESIZE: self.scr.refresh()
            if c == ord('m'): 
                self.scr.erase()                
                
                try:
                    self.mode = self.itermodes.next()(self.scr)
                except StopIteration:
                    self.itermodes = iter(self.modes)
                    self.mode = self.itermodes.next()(self.scr)
                    
                self.mode.draw_header()
            
            for id, stat in enumerate(self.a2stat):
                try:
                    self.mode.draw_updateing(stat, id)
                    stat.update()
                    self.mode.draw(stat, id)
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
    parser.add_option("-m", "--mode", action="store", type="string", dest="mode", default="Widescreen", help="use this drawing mode [Widescreen, Tabular]")
    
    (options, args) = parser.parse_args(sys.argv[1:])
    if options.mode.upper() == "WIDESCREEN":
        options.mode = ApacheTopWidescreen
    elif  options.mode.upper() == "TABULAR":
        options.mode = ApacheTopTabular
    else:
        options.mode = ApacheTopWidescreen

    a2top = ApacheTop(hosts=args, mode = options.mode, interval=options.interval)
    a2top.run()

if __name__ == '__main__':
    main()
