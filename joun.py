import configparser
import os
import re
import select
from enum import Enum
from pathlib import Path
from typing import Mapping, Any, List

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
        config_dir_path = Path.home().joinpath('.config').joinpath('jnotify')
        if not config_dir_path.parent.is_dir():
            os.makedirs(config_dir_path)
        self.config_path: Path = config_dir_path.joinpath('jnotify.conf')
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
        sep = ''
        for journal_entry in journal_entries:
            for key, prefix in {'SYSLOG_IDENTIFIER': '', '_PID': 'PID ', '_CMDLINE': '', '_EXE': '', '_COMM': '',
                                '_KERNEL_SUBSYSTEM': 'kernel ',
                                }.items():
                print(key, journal_entry[key] if key in journal_entry else False)
                if key in journal_entry:
                    value = str(journal_entry[key])
                    if app_name_info.find(value) < 0:
                        app_name_info += sep + prefix + value
                        sep = '; '
        if app_name_info == '':
            app_name_info = 'unknown'
        return app_name_info

    def determine_summary(self, journal_entries: List[Mapping[str, Any]]):
        journal_entry = journal_entries[0]
        realtime = journal_entry['__REALTIME_TIMESTAMP']
        transport = f" {journal_entry['_TRANSPORT']}:" if '_TRANSPORT' in journal_entry else ''
        number_of_entries = len(journal_entries)
        if number_of_entries > 1:
            summary = f"{realtime:%H:%M:%S}:{transport} Burst of {number_of_entries} messages"
        else:
            if 'SYSLOG_IDENTIFIER' in journal_entry:
                text = journal_entry['SYSLOG_IDENTIFIER']
            else:
                text = journal_entry['MESSAGE']
            summary = f"{realtime:%H:%M:%S}: {transport} {text}"
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
                message += f"{sep}{new_message}"
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


def main():
    journal_watcher = JournalWatcher()
    journal_watcher.watch_journal()


if __name__ == '__main__':
    main()
