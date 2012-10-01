# a2top - Apache2 Top

A small program providing a simple top-like curses gui to monitor one or multiple local or remote installations of 
apache2 using mod_status.

### Usage
``` bash
$ a2top.py --help
usage: a2top.py [-h] [-i INTERVAL] [-m {Widescreen,Tabular}] hosts [hosts ...]

Show Apache2 server statistics via mod_status

positional arguments:
  hosts                 apache server to check

optional arguments:
  -h, --help            show this help message and exit
  -i INTERVAL, --interval INTERVAL
                        interval for updateing server infos
  -m {Widescreen,Tabular}, --mode {Widescreen,Tabular}
                        use this drawing mode

EXAMPLE: a2top http://example.com/server-status?auto


$ a2top --interval 5 http://server{1..5}/system-status?auto
```

Widescreen recommended! :D

### Screenshots

Widescreen Mode (Maximum details, for monitoring only one or two servers)
![Screenshot](https://raw.github.com/Crapworks/a2top/master/screenshots/mode1.png)

Tabular Mode (Less Details, but far more informations and servers on one screen)
![Screenshot](https://raw.github.com/Crapworks/a2top/master/screenshots/mode2.png)

