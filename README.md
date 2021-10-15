jouno: Journal notifications forwarder
======================================

A [Systemd Journal](https://www.freedesktop.org/software/systemd/man/systemd-journald.service.html) 
to [Freedesktop Notifications](https://specifications.freedesktop.org/notification-spec/latest/ar01s09.html) 
forwarder with burst-handling and filtering.

Description
-----------

This software is currently pre-release, It is feature complete and quite usable but may lack some polish.

![Default](screen-shots/Screenshot_Large.png) 

Getting Started
---------------

``jouno`` A desktop journal-entry to desktop-notification forwarder with message filtering capabilities.

The application monitors the systemd-journal for new entries, filters them, and forwards them to the 
standard ``freedesktop`` ``dbus`` notifications interface.  Typically desktops present notifications
as popup messages.

Bursts of messages are handled by bundling them in to a single summarising notification.

``jouno`` runs as a system-tray application.

To get started with ``jouno``, you only need to download the ``jouno.py`` python script and
check that the dependencies described below are in place. 


Dependencies
------------

All the following runtime dependencies are likely to be available pre-packaged on any modern Linux distribution 
(``vdu_controls`` was originally developed on OpenSUSE Tumbleweed).

* python 3.8: ``journo`` is written in python and may depend on some features present only in 3.8 onward.
* python 3.8 QtPy: the python GUI library used by ``vdu_controls``.
* python 3.8 systemd: python module for native access to the systemd facilities.


Installing
----------

As previously stated, the ``jouno.py`` script is only file required beyond the prerequisites. 

Executing the program
---------------------

  ``% python3 jouno.py``

Help
----

Detailed help can be accessed by using the right mouse-button to bring up a context-menu.  Access to the context-menu
is available in the application-window and in the system-tray icon.

* Configuration file in `$HOME/.config/jouno/journo.conf`


Development
-----------

At this time there is only one real source file, ``journo.py``

My IDE for this project is [PyCharm Community Edition](https://www.jetbrains.com/pycharm/).

My development Linux desktop is [OpenSUSE Tumbleweed](https://get.opensuse.org/tumbleweed/). The python3
interpreter and python3 libraries are from the standard OpenSUSE Tumbleweed repositories (Tumbleweed currently
defaults python3 to [python 3.8](https://www.python.org/downloads/release/python-380/)).

Authors
-------

Michael Hamilton\
``m i c h a e l   @  a c t r i x   .   g e n  . n z``


Version History
---------------

``jouno`` is currently still in development. It is feature complete and quite functional, but no formal release 
has been made.


License
-------

This project is licensed under the **GNU General Public License Version 3** - see the [LICENSE.md](LICENSE.md) file 
for details

**jouno Copyright (C) 2021 Michael Hamilton**

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, version 3.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see <https://www.gnu.org/licenses/>.

## Acknowledgments

* [pyqt](https://riverbankcomputing.com/software/pyqt/)
* [Systemd Journal](https://www.freedesktop.org/software/systemd/man/systemd-journald.service.html) 
* [Freedesktop Notifications](https://specifications.freedesktop.org/notification-spec/latest/ar01s09.html)