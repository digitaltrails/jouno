import select
from typing import Mapping, Any

import dbus
from systemd import journal

import configparser


# Press Alt+Shift+X to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

class NotifyFreeDesktop:

    def __init__(self):
        self.notify_interface = dbus.Interface(
            object=dbus.SessionBus().get_object("org.freedesktop.Notifications", "/org/freedesktop/Notifications"),
            dbus_interface="org.freedesktop.Notifications")

    def notify_desktop(self, app_name: str, summary: str, message: str):
        replace_id = 0
        notification_icon = ''
        action_requests = []
        extra_hints = {"urgency": 1}
        timeout = 60000
        self.notify_interface.Notify(app_name, replace_id, notification_icon, summary, message, action_requests,
                                     extra_hints,
                                     timeout)


class JournalWatcher:

    def __init__(self, config: configparser.ConfigParser):
        self.config = config

    def determine_app_name(self, journal_entry: Mapping[str, Any]):
        app_name_info = ''
        sep = ''
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

    def determine_summary(self, journal_entry: Mapping[str, Any], burst_count: int = 0):
        realtime = journal_entry['__REALTIME_TIMESTAMP']
        transport = f" {journal_entry['_TRANSPORT']}:" if '_TRANSPORT' in journal_entry else ''
        print(realtime)
        if burst_count > 1:
            summary = f"{realtime:%H:%M:%S}:{transport} Burst of {burst_count} messages, first was..."
        else:
            if 'SYSLOG_IDENTIFIER' not in journal_entry:
                text = journal_entry['SYSLOG_IDENTIFIER']
            else:
                text = journal_entry['MESSAGE']
            summary = f"{realtime:%H:%M:%S}: {transport} {text} "
        print("summary=", summary)
        return summary

    def determine_message(self, journal_entry: Mapping[str, Any]) -> str:
        message = journal_entry['MESSAGE']
        print(message)
        return f"{message}"

    def is_notable(self, journal_entry: Mapping[str, Any]):
        message = journal_entry['MESSAGE']
        if message != "":
            for ignore_key, ignore_spec in self.config['IGNORE'].items():
                if ignore_spec in message:
                    print(f"Ignore option {ignore_key} ignoring: {message}")
                    return False
        return True

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
            burst_count = 0
            first_notable = None
            while journal_reader_poll.poll(2000):
                if journal_reader.process() == journal.APPEND:
                    for journal_entry in journal_reader:
                        burst_count += 1
                        if self.is_notable(journal_entry):
                            if first_notable is None:
                                first_notable = journal_entry
                        if first_notable:
                            print(f"count={burst_count} {journal_entry['MESSAGE']}")
            if first_notable is not None:
                notify.notify_desktop(app_name=self.determine_app_name(first_notable),
                                      summary=self.determine_summary(first_notable, burst_count=burst_count),
                                      message=self.determine_message(first_notable))


def main():
    config = configparser.ConfigParser()
    config['IGNORE'] = {'kwin_bad_damage': 'XCB error: 152 (BadDamage)',
                        'kwin_bad_window': 'kwin_core: XCB error: 3 (BadWindow)',
                        'xyzzy': 'xyzzy',
                        'self_caused': 'NotificationPopup.',
                        'qt_kde_binding_loop': 'Binding loop detected for property'}
    journal_watcher = JournalWatcher(config)
    journal_watcher.watch_journal()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

    # j = journal.Reader()
    # #j.log_level(journal.LOG_INFO)
    #
    # # j.add_match(_SYSTEMD_UNIT="systemd-udevd.service")
    # j.seek_tail()
    # j.get_previous()
    # # j.get_next() # it seems this is not necessary.
    #
    # p = select.poll()
    # p.register(j, j.get_events())
    #
    # while p.poll():
    #     if j.process() != journal.APPEND:
    #         continue
    #     for entry in j:
    #         if entry['MESSAGE'] != "":
    #             print(str(entry['__REALTIME_TIMESTAMP'] )+ ' ' + entry['MESSAGE'])
    #             print(entry)
    #             notify_interface.Notify("x", 0, "x", 'summary', entry['MESSAGE'], [], {"urgency": 1}, 10000)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
