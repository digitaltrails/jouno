jouno: Journal notifications forwarder
======================================

A [Systemd Journal](https://www.freedesktop.org/software/systemd/man/systemd-journald.service.html) 
to [Freedesktop Notifications](https://specifications.freedesktop.org/notification-spec/latest/ar01s09.html) 
forwarder with burst-handling and filtering.

Description
-----------

This software is currently pre-release, It is feature complete and quite usable but may lack some polish.

![Default](screen-shots/Screenshot_Large.png) 

``jouno,`` is system-tray application for monitoring the ``systemd-journal.`` It raises selected 
entries as desktop-notifications.

The application monitors the ``systemd-journal`` for new entries, filters them, and forwards them as 
standard ``freedesktop dbus notifications``.  Most linux desktops present these notifications
as individual popup messages.

Bursts of messages are handled by bundling them in to a single summarising notification.

``jouno`` is a tool designed to improve awareness of background activity by monitoring
the journal and raising interesting journal-entries as desktop notifications.  Possibilities for 
it use include:

 * Monitoring specific jobs, such as the progress of the daily backups.
 * Watching for specific events, such as background core dumps.
 * Investigating desktop actions that raise journal log entries.
 * Discovering unnecessary daemon activity and unnecessary services.
 * Notifying access attempts, such as su, ssh, samba, or pam events.
 * Prevention of undesirable desktop activity, such as shutting down during the backups.
 * Detecting hardware events. 
 * Raising general awareness of what is going on in the background.

I have previously released a gist [notify-desktop](https://gist.github.com/digitaltrails/26aad3282d8739db1de8bc2e59c812eb)
that allows root batch-jobs, such as my daily backups, to raise notifications for the current desktop 
user, but ``notify-desktop`` only covers my own code.  ``jouno`` allows me to watch for and monitor any
jobs on the system and potentially removes the need for my jobs to use my ``notify-desktop`` script.


Getting Started
---------------


To get started with ``jouno``, you only need to download the ``jouno.py`` python script and
check that the dependencies described below are in place. 


Dependencies
------------

All the following runtime dependencies are likely to be available pre-packaged on any modern Linux distribution 
(``jouno`` was originally developed on OpenSUSE Tumbleweed).

* python 3.8: ``journo`` is written in python and may depend on some features present only in 3.8 onward.
* python 3.8 QtPy: the python GUI library used by ``jouno``.
* python 3.8 systemd: python module for native access to the systemd facilities.
* python 3.8 dbus: python module for dbus used for issuing notifications

Dependency installation on ``OpenSUSE``::

        zypper install python38-QtPy python38-systemd python38-dbus

Installing
----------

As previously stated, the ``jouno.py`` script is only file required beyond the prerequisites. 

The current options for installation are the following:

1. The script can be run without installation by using a python interpreter, for example:
   ```
   % python3 jouno.py
   ```
2. The script can be self installed as desktop application in the current user's desktop menu 
   as *Applications->Settings->VDU Controls* by running:
   ```
    % python3 jouno.py --install
   ```
      Depending on which desktop you're running menu changes may require logout before they become visible.


Executing the program
---------------------

  ``% python3 jouno.py``

Help
----

Detailed help can be accessed by using the right mouse-button to bring up a context-menu.  Access to the context-menu
is available in the application-window and in the system-tray icon.

* Configuration file in `$HOME/.config/jouno/journo.conf`

Issues
------

KDE kwin-compositing has an ongoing CPU/responsiveness issue for notifications that are set to expire ([bug 436240](https://bugs.kde.org/show_bug.cgi?id=436240)).
If this proves to be a problem, the ``jouno`` option notification_seconds can be set to zero, in 
which case popup messages won't expire and will remain visible until dismissed.  

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