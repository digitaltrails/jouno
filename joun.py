#!/usr/bin/python3
"""
joun: Journal notifications forwarder
=====================================

A desktop journal-entry to desktop-notification forwarder.

Usage:
======

        joun [-h]
                     [--about] [--detailed-help]
                     [--create-config-files]
                     [--install] [--uninstall]

Optional arguments:
-------------------

      -h, --help            show this help message and exit
      --detailed-help       full help in markdown format
      --about               about joun
      --debug               enable debug output to stdout
      --create-config-files  if they do not exist, create template config INI files in $HOME/.config/joun/
      --install             installs the joun in the current user's path and desktop application menu.
      --uninstall           uninstalls the joun application menu file and script for the current user.

Description
===========

``joun`` A desktop journal-entry to desktop-notification forwarder with a range of filtering capabilities.
The systemd-journal is continuously monitored for new entries which are then filtered to select those that
need to be forwarded to the standard ``freedesktop`` ``dbus`` notifications interface.  Bursts of messages
are handled by bundling them in to single summarising notification.

Configuration
=============

Configuration is supplied via command line parameters and config-files.  The command line provides an immediate way
to temporarily alter the behaviour of the application. The config files provide a more comprehensive and permanent
solution for altering the application's configuration.

Settings Menu and Config files
------------------------------

The right-mouse context-menu ``Settings`` item can be used to customise the application by writing to a set of config
files.  The ``Settings`` item will feature a tab for editing each config file.

The config files are in INI-format divided into a number of sections as outlined below:

        # The vdu-controls-globals section is only required in $HOME/.config/vdu_controls/vdu_controls.conf
        [options]
        burst_seconds = 2
        burst_truncate_messages = 3
        debug = yes

        [match]
        my_rule_name = forward journal entry if this string matches
        my_other_rule_name = regexp forward journal [Ee]ntry if this python-regexp matches

        [ignore]
        my_ignore_rule_name = ignore journal entry if this string matches
        my_ignore_other_rule_name = regexp ignore [Jj]ournal entry if this python-regexp matches

As well as using the ``Settings``, config files may also be created by the command line option

        joun --create-config-files

which will create initial templates based on the currently connected VDU's.

The config files are completely optional, but some filtering of the journal is likely to be necessary.
For example, some KDE desktop-notification processing can cause KDE errors which will be logged to
the journal.  It may be that desktops other than KDE may log fewer or no errors during notification
processing.  ``joun`` copes with cascades and won't cause infinite cascades, but filtering is
necessary to shut them up the initial bursts.


Responsiveness
--------------

Filter more...

Examples
========

    joun
        All default controls.



Prerequisites
=============

Described for OpenSUSE, similar for other distros:

Software::

        zypper install python38-QtPy python38-systemd

Kernel Modules::

        lsmod | grep i2c_dev

Read ddcutil readme concerning config of i2c_dev with nvidia GPU's. Detailed ddcutil info at https://www.ddcutil.com/


joun Copyright (C) 2021 Michael Hamilton
===========================================

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, version 3.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see <https://www.gnu.org/licenses/>.

**Contact:**  m i c h a e l   @   a c t r i x   .   g e n   .   n z

----------

# ######################## MONITOR SUB PROCESS CODE ###############################################################


"""

import configparser
import os
import re
import select
import traceback
from enum import Enum
from pathlib import Path
from typing import Mapping, Any, List, Type
import signal
import sys
import multiprocessing as mp

from PyQt5.QtCore import QCoreApplication, QProcess, Qt
from PyQt5.QtGui import QPixmap, QIcon, QImage, QPainter, QCursor
from PyQt5.QtSvg import QSvgWidget, QSvgRenderer
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QSlider, QMessageBox, QLineEdit, QLabel, \
    QSplashScreen, QPushButton, QProgressBar, QComboBox, QSystemTrayIcon, QMenu, QStyle, QTextEdit, QDialog, QTabWidget, \
    QCheckBox, QPlainTextEdit, QGridLayout, QSizePolicy, QAction
import dbus
from systemd import journal

DEFAULT_CONFIG = '''
[options]
burst_seconds = 2
burst_truncate_messages = 3
notification_seconds = 60
debug = yes

[ignore] 
kwin_bad_damage = XCB error: 152 (BadDamage)
kwin_bad_window = kwin_core: XCB error: 3 (BadWindow)
self_caused = NotificationPopup.
qt_kde_binding_loop = Binding loop detected for property

[match]

'''


class Priority(Enum):
    EMERGENCY = 0
    ALERT = 1
    CRITICAL = 2
    ERR = 3
    WARNING = 4
    NOTICE = 5
    INFO = 6
    DEBUG = 7


NOTIFICATION_ICONS = {
    Priority.EMERGENCY: 'dialog-error.png',
    Priority.ALERT: 'dialog-error.png',
    Priority.CRITICAL: 'dialog-error.png',
    Priority.ERR: 'dialog-error.png',
    Priority.WARNING: 'dialog-warning.png',
    Priority.NOTICE: 'dialog-information.png',
    Priority.INFO: 'dialog-information.png',
    Priority.DEBUG: 'dialog-information.png',
}


# Press Alt+Shift+X to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

class NotifyFreeDesktop:

    def __init__(self):
        self.notify_interface = dbus.Interface(
            object=dbus.SessionBus().get_object("org.freedesktop.Notifications", "/org/freedesktop/Notifications"),
            dbus_interface="org.freedesktop.Notifications")

    def notify_desktop(self, app_name: str, summary: str, message: str, priority: Priority, timeout: int):
        # https://specifications.freedesktop.org/notification-spec/notification-spec-latest.html
        replace_id = 0
        notification_icon = NOTIFICATION_ICONS[priority]
        action_requests = []
        extra_hints = {"urgency": 1, "sound-name": "dialog-warning", }
        self.notify_interface.Notify(app_name, replace_id, notification_icon, summary, message, action_requests,
                                     extra_hints,
                                     timeout)


class JournalWatcher:

    def __init__(self):
        config_dir_path = Path.home().joinpath('.config').joinpath('joun')
        if not config_dir_path.parent.is_dir():
            os.makedirs(config_dir_path)
        self.config_path: Path = config_dir_path.joinpath('joun.conf')
        self.config: configparser.ConfigParser = None
        self.config_mtime: float = 0.0
        self.burst_truncate: int = 3
        self.polling_millis: int = 2000
        self.notification_timeout: int = 60000
        self.debug_enabled: bool = True
        self.ignore_regexp: Mapping[str, re] = {}
        self.match_regexp: Mapping[str, re] = {}
        self.update_config()

    def update_config(self):
        if self.config_path.is_file():
            mtime = self.config_path.lstat().st_mtime
            if self.config is not None and self.config_mtime == mtime:
                return
            self.config_mtime = mtime
            self.info(f"Reading {self.config_path}")
            config_text = Path(self.config_path).read_text()
        elif self.config is None:
            self.info(f"No {self.config_path}")
            config_text = DEFAULT_CONFIG
        else:
            return
        config = configparser.ConfigParser()
        config.read_string(config_text)
        for section in ['options', 'match', 'ignore']:
            if section not in config:
                config[section] = {}
        self.config = config
        if 'burst_truncate_messages' in self.config['options']:
            self.burst_truncate = self.config.getint('options', 'burst_truncate_messages')
        if 'burst_seconds' in self.config['options']:
            self.polling_millis = 1000 * self.config.getint('options', 'burst_seconds')
        if 'notification_seconds' in self.config['options']:
            self.notification_timeout = 1000 * self.config.getint('options', 'notification_seconds')
        if 'debug' in self.config['options']:
            self.debug_enabled = self.config.getboolean('options', 'debug')
        for rule_id, rule_text in self.config['ignore'].items():
            if rule_text.startswith('regexp '):
                self.ignore_regexp[rule_id] = re.compile(rule_text[len('regexp '):])
            else:
                self.ignore_regexp[rule_id] = re.compile(re.escape(rule_text))
        for rule_id, rule_text in self.config['match'].items():
            if rule_text.startswith('regexp '):
                self.match_regexp[rule_id] = re.compile(rule_text[len('regexp '):])
            else:
                self.match_regexp[rule_id] = re.compile(re.escape(rule_text))

    def determine_app_name(self, journal_entries: List[Mapping[str, Any]]):
        app_name_info = ''
        sep = '\u25b3'
        for journal_entry in journal_entries:
            for key, prefix in {'_CMDLINE': '', '_EXE': '', '_COMM': '', 'SYSLOG_IDENTIFIER': '',
                                '_KERNEL_SUBSYSTEM': 'kernel ',
                                }.items():
                print(key, journal_entry[key] if key in journal_entry else False)
                if key in journal_entry:
                    value = str(journal_entry[key])
                    if app_name_info.find(value) < 0:
                        app_name_info += sep + prefix + value
                        sep = '; '
        if app_name_info == '':
            app_name_info = sep + 'unknown'
        return app_name_info

    def determine_summary(self, journal_entries: List[Mapping[str, Any]]):
        journal_entry = journal_entries[0]
        realtime = journal_entry['__REALTIME_TIMESTAMP']
        transport = f" {journal_entry['_TRANSPORT']}" if '_TRANSPORT' in journal_entry else ''
        number_of_entries = len(journal_entries)
        if number_of_entries > 1:
            summary = f"\u25F4{realtime:%H:%M:%S}:{transport} Burst of {number_of_entries} messages"
        else:
            text = ''
            sep = ''
            for key, prefix in {'SYSLOG_IDENTIFIER': '', '_PID': 'PID ', '_KERNEL_SUBSYSTEM': 'kernel ', }.items():
                if key in journal_entry:
                    value = str(journal_entry[key])
                    if text.find(value) < 0:
                        text += sep + prefix + value
                        sep = ' '
            summary = f"\u25F4{realtime:%H:%M:%S}: {text} (\u21e8{transport})"
        self.debug(f"realtime='{realtime}' summary='{summary}'")
        return summary

    def determine_message(self, journal_entries: List[Mapping[str, Any]]) -> str:
        message = ''
        sep = ''
        previous_message = ''
        duplicates = 0
        reported = 0
        for journal_entry in journal_entries:
            new_message = journal_entry['MESSAGE']
            if new_message == previous_message:
                duplicates += 1
            else:
                message += f"{sep}\u25B7{new_message}"
                previous_message = new_message
                reported += 1
                if reported == self.burst_truncate and reported < len(journal_entries):
                    message += f"\n[Only showing first {self.burst_truncate} messages]"
                    break
            sep = '\n'
        if duplicates > 0:
            message += f'\n[{duplicates + 1} duplicate messages]'
        self.debug(f'message={message}')
        return message

    def determine_priority(self, journal_entries: List[Mapping[str, Any]]) -> Priority:
        current_level = Priority.NOTICE
        for journal_entry in journal_entries:
            if 'PRIORITY' in journal_entry:
                priority = journal_entry['PRIORITY']
                if priority < current_level.value and (Priority.EMERGENCY.value <= priority <= Priority.DEBUG.value):
                    current_level = Priority(priority)
        return current_level

    def is_notable(self, journal_entry: Mapping[str, Any]):
        message = journal_entry['MESSAGE']
        if message != "":
            for rule_id, match_re in self.match_regexp.items():
                if match_re.search(message) is not None:
                    self.debug(f"rule=match.{rule_id}: {message}")
                    return True
            for rule_id, ignore_re in self.ignore_regexp.items():
                if ignore_re.search(message) is not None:
                    self.debug(f"rule=ignore.{rule_id}: {message}")
                    return False
        return len(self.match_regexp) == 0

    def watch_journal(self):
        notify = NotifyFreeDesktop()

        journal_reader = journal.Reader()
        # #j.log_level(journal.LOG_INFO)
        #
        # # j.add_match(_SYSTEMD_UNIT="systemd-udevd.service")
        journal_reader.seek_tail()
        journal_reader.get_previous()
        # j.get_next() # it seems this is not necessary.

        journal_reader_poll = select.poll()
        journal_reader_poll.register(journal_reader, journal_reader.get_events())
        journal_reader.add_match()
        while True:
            self.update_config()
            burst_count = 0
            notable = []
            while journal_reader_poll.poll(self.polling_millis):
                if journal_reader.process() == journal.APPEND:
                    for journal_entry in journal_reader:
                        burst_count += 1
                        if self.is_notable(journal_entry):
                            self.debug(f"Notable: burst_count={len(notable)}: {journal_entry}")
                            self.debug(f"Notable: burst_count={len(notable)}: {journal_entry['MESSAGE']}")
                            notable.append(journal_entry)
            if len(notable):
                notify.notify_desktop(app_name=self.determine_app_name(notable),
                                      summary=self.determine_summary(notable),
                                      message=self.determine_message(notable),
                                      priority=self.determine_priority(notable),
                                      timeout=self.notification_timeout)

    def debug(self, *arg):
        if self.debug_enabled:
            print('DEBUG:', *arg)

    def info(self, *arg):
        print('INFO:', *arg)


def translate(source_text: str):
    """For future internationalization - recommended way to do this at this time."""
    return QCoreApplication.translate('vdu_controls', source_text)

# ######################## USER INTERFACE CODE ######################################################################

joun_VERSION = '0.9.0'

ABOUT_TEXT = f"""

<b>joun version {joun_VERSION}</b>
<p>
A journal-entry to desktop-notification forwarder. 
<p>
Run joun --help in a console for help.
<p>
Visit <a href="https://github.com/digitaltrails/joun">https://github.com/digitaltrails/joun</a> for 
more details.
<p><p>

<b>joun Copyright (C) 2021 Michael Hamilton</b>
<p>
This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the
Free Software Foundation, version 3.
<p>
This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
more details.
<p>
You should have received a copy of the GNU General Public License along
with this program. If not, see <a href="https://www.gnu.org/licenses/">https://www.gnu.org/licenses/</a>.

"""

CONTRAST_SVG = b"""
<svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="0 0 24 24" width="24" height="24">
  <defs>
    <style type="text/css" id="current-color-scheme">
      .ColorScheme-Text { color:#232629; }
    </style>
  </defs>
  <g transform="translate(1,1)">
    <path style="fill:currentColor;fill-opacity:1;stroke:none" transform="translate(-1,-1)" d="m 12,7 c -2.761424,0 -5,2.2386 -5,5 0,2.7614 2.238576,5 5,5 2.761424,0 5,-2.2386 5,-5 0,-2.7614 -2.238576,-5 -5,-5 z m 0,1 v 8 C 9.790861,16 8,14.2091 8,12 8,9.7909 9.790861,8 12,8" class="ColorScheme-Text" id="path79" />
  </g>
</svg>
"""

# https://www.svgrepo.com/svg/335387/filter
FILTER_SVG = b"""
<svg width="24px" height="24px" viewBox="0 -1 18 19" xmlns="http://www.w3.org/2000/svg">
  <path fill="#494c4e" d="M14.35 4.855L10 9.21v2.8c0 1.31-2 2.45-2 1.89V9.2L3.65 4.856a.476.476 0 0 1-.11-.54A.5.5 0 0 1 4 4h10a.5.5 0 0 1 .46.31.476.476 0 0 1-.11.545z"/>
  <circle fill="#494c4e" cx="9" cy="17" r="1"/>
  <circle fill="#494c4e" cx="5" cy="1" r="1"/>
  <circle fill="#494c4e" cx="13" cy="1" r="1"/>
  <circle fill="#494c4e" cx="9" cy="1" r="1"/>
</svg>
"""

FILTER_OFF_SVG = b"""
<svg width="24px" height="24px" viewBox="0 -1 18 19" xmlns="http://www.w3.org/2000/svg">
  <path fill="#494c4e" d="M14.35 4.855L10 9.21v2.8c0 1.31-2 2.45-2 1.89V9.2L3.65 4.856a.476.476 0 0 1-.11-.54A.5.5 0 0 1 4 4h10a.5.5 0 0 1 .46.31.476.476 0 0 1-.11.545z"/>
  <circle fill="#ff5500" cx="9" cy="17" r="1"/>
  <circle fill="#ff5500" cx="5" cy="1" r="1"/>
  <circle fill="#ff5500" cx="13" cy="1" r="1"/>
  <circle fill="#ff5500" cx="9" cy="1" r="1"/>
</svg>
"""

def create_icon_from_svg_string(svg_str: bytes) -> QIcon:
    """There is no QIcon option for loading SVG from a string, only from a SVG file, so roll our own."""
    renderer = QSvgRenderer(svg_str)
    image = QImage(64, 64, QImage.Format_ARGB32)
    image.fill(0x0)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    return QIcon(QPixmap.fromImage(image))


class ConfigEditorWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(translate('Control Panel'))
        self.setMinimumWidth(1024)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.make_visible()

    def make_visible(self):
        """
        If the dialog exists(), call this to make it visible by raising it.
        Internal, used by the class method show_existing_dialog()
        """
        self.show()
        self.raise_()
        self.activateWindow()


class DialogSingletonMixin:
    """
    A mixin that can augment a QDialog or QMessageBox with code to enforce a singleton UI.
    For example, it is used so that only ones settings editor can be active at a time.
    """
    _dialogs_map = {}
    debug = False

    def __init__(self) -> None:
        """Registers the concrete class as a singleton so it can be reused later."""
        super().__init__()
        class_name = self.__class__.__name__
        if class_name in DialogSingletonMixin._dialogs_map:
            raise TypeError(f"ERROR: More than one instance of {class_name} cannot exist.")
        if DialogSingletonMixin.debug:
            print(f'DEBUG: SingletonDialog created for {class_name}')
        DialogSingletonMixin._dialogs_map[class_name] = self

    def closeEvent(self, event) -> None:
        """Subclasses that implement their own closeEvent must call this closeEvent to deregister the singleton"""
        class_name = self.__class__.__name__
        if DialogSingletonMixin.debug:
            print(f'DEBUG: SingletonDialog remove {class_name}')
        del DialogSingletonMixin._dialogs_map[class_name]
        event.accept()

    def make_visible(self):
        """
        If the dialog exists(), call this to make it visible by raising it.
        Internal, used by the class method show_existing_dialog()
        """
        self.show()
        self.raise_()
        self.activateWindow()

    @classmethod
    def show_existing_dialog(cls: Type):
        """If the dialog exists(), call this to make it visible by raising it."""
        class_name = cls.__name__
        if DialogSingletonMixin.debug:
            print(f'DEBUG: SingletonDialog show existing {class_name}')
        instance = DialogSingletonMixin._dialogs_map[class_name]
        instance.make_visible()

    @classmethod
    def exists(cls: Type) -> bool:
        """Returns true if the dialog has already been created."""
        class_name = cls.__name__
        if DialogSingletonMixin.debug:
            print(f'DEBUG: SingletonDialog exists {class_name} {class_name in DialogSingletonMixin._dialogs_map}')
        return class_name in DialogSingletonMixin._dialogs_map


class AboutDialog(QMessageBox, DialogSingletonMixin):

    @staticmethod
    def invoke():
        if AboutDialog.exists():
            AboutDialog.show_existing_dialog()
        else:
            AboutDialog()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(translate('About'))
        self.setTextFormat(Qt.AutoText)
        self.setText(translate('About joun'))
        self.setInformativeText(translate(ABOUT_TEXT))
        self.setIcon(QMessageBox.Information)
        self.exec()


class HelpDialog(QDialog, DialogSingletonMixin):

    @staticmethod
    def invoke():
        if HelpDialog.exists():
            HelpDialog.show_existing_dialog()
        else:
            HelpDialog()

    def __init__(self):
        super().__init__()
        self.setWindowTitle(translate('Help'))
        layout = QVBoxLayout()
        markdown_view = QTextEdit()
        markdown_view.setReadOnly(True)
        markdown_view.setMarkdown(__doc__)
        layout.addWidget(markdown_view)
        self.setLayout(layout)
        # TODO maybe compute a minimum from the actual screen size
        self.setMinimumWidth(1600)
        self.setMinimumHeight(1024)
        # .show() is non-modal, .exec() is modal
        self.make_visible()


class ContextMenu(QMenu):

    def __init__(self,
                 about_action=None, help_action=None, enable_action=None,
                 quit_action=None) -> None:
        super().__init__()
        self.main_window = None

        toggle_action = self.addAction(
            self.style().standardIcon(QStyle.SP_ComputerIcon),
            translate('Pause'),
            enable_action)
        self.addAction(self.style().standardIcon(QStyle.SP_MessageBoxInformation),
                       translate('About'),
                       about_action)
        self.addAction(self.style().standardIcon(QStyle.SP_TitleBarContextHelpButton),
                       translate('Help'),
                       help_action)
        self.addSeparator()
        self.addAction(self.style().standardIcon(QStyle.SP_DialogCloseButton),
                       translate('Quit'),
                       quit_action)

        def triggered(action: QAction):
            print('triggered', action.text(), toggle_action.text())
            if action == toggle_action:
                action.setText(translate('Continue') if action.text() == translate("Pause") else translate("Pause"))

        self.triggered.connect(triggered)

    def set_vdu_controls_main_window(self, main_window) -> None:
        self.main_window = main_window


def exception_handler(e_type, e_value, e_traceback):
    """Overarching error handler in case something unexpected happens."""
    print("ERROR:\n", ''.join(traceback.format_exception(e_type, e_value, e_traceback)))
    alert = QMessageBox()
    alert.setText(translate('Error: {}').format(''.join(traceback.format_exception_only(e_type, e_value))))
    alert.setInformativeText(translate('Unexpected error'))
    alert.setDetailedText(
        translate('Details: {}').format(''.join(traceback.format_exception(e_type, e_value, e_traceback))))
    alert.setIcon(QMessageBox.Critical)
    alert.exec()
    QApplication.quit()




def user_interface():
    sys.excepthook = exception_handler

    app = QApplication(sys.argv)

    def toggle_watcher() -> None:
        global watcher_process
        if watcher_process.is_alive():
            stop_watch_journal()
            tray.setIcon(watch_off_icon)
        else:
            start_watch_journal()
            tray.setIcon(watch_on_icon)

    app_context_menu = ContextMenu(about_action=AboutDialog.invoke,
                                   help_action=HelpDialog.invoke,
                                   enable_action=toggle_watcher,
                                   quit_action=app.quit)

    watch_on_icon = create_icon_from_svg_string(FILTER_SVG)
    watch_off_icon = create_icon_from_svg_string(FILTER_OFF_SVG)

    tray = QSystemTrayIcon()
    tray.setIcon(watch_on_icon)
    tray.setContextMenu(app_context_menu)

    app.setWindowIcon(watch_on_icon)
    app.setApplicationDisplayName(translate('Journal Notification Forwarder'))

    main_window = ConfigEditorWidget()

    def show_window():
        if main_window.isVisible():
            main_window.hide()
        else:
            # Use the mouse pos as a guess to where the system tray is.  The Linux Qt x,y geometry returned by
            # the tray icon is 0,0, so we can't use that.
            p = QCursor.pos()
            wg = main_window.geometry()
            # Also try to cope with the tray not being at the bottom right of the screen.
            x = p.x() - wg.width() if p.x() > wg.width() else p.x()
            y = p.y() - wg.height() if p.y() > wg.height() else p.y()
            main_window.setGeometry(x, y, wg.width(), wg.height())
            main_window.show()
            # Attempt to force it to the top with raise and activate
            main_window.raise_()
            main_window.activateWindow()

    tray.activated.connect(show_window)
    tray.setVisible(True)
    rc = app.exec_()
    if rc == 999:  # EXIT_CODE_FOR_RESTART:
        QProcess.startDetached(app.arguments()[0], app.arguments()[1:])


def watch_journal():
    journal_watcher = JournalWatcher()
    journal_watcher.watch_journal()


watcher_process: mp.Process = None


def start_watch_journal():
    global watcher_process
    if watcher_process is not None and watcher_process.is_alive():
        watcher_process.terminate()
    watcher_process = mp.Process(target=watch_journal, args=())
    watcher_process.start()
    print(f"started watcher PID={watcher_process.pid}")


def stop_watch_journal():
    global watcher_process
    if watcher_process is not None and watcher_process.is_alive():
        watcher_process.terminate()
        watcher_process.join()
        print(f"terminated watcher PID={watcher_process.pid} exit code={watcher_process.exitcode}")


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    start_watch_journal()
    user_interface()


if __name__ == '__main__':
    main()
