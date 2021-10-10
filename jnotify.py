import select

import dbus
from systemd import journal
# This is a sample Python script.
from notify2 import Notification

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

    def determine_app_name(self, entry):
        app_name_info = ''
        sep = ''
        for key, prefix in {'SYSLOG_IDENTIFIER': '', '_PID': 'PID ', '_CMDLINE': '', '_EXE': '', '_COMM': '',
                            '_KERNEL_SUBSYSTEM': 'kernel ',
                            }.items():
            print(key, entry[key] if key in entry else False)
            if key in entry:
                value = str(entry[key])
                if app_name_info.find(value) < 0:
                    app_name_info += sep + prefix + value
                    sep = '; '
        if app_name_info == '':
            app_name_info = 'unknown'
        return app_name_info


    def determine_summary(self, entry, burst_count: int = 0):
        realtime = entry['__REALTIME_TIMESTAMP']
        transport = f" {entry['_TRANSPORT']}:" if '_TRANSPORT' in entry else ''
        print(realtime)
        if burst_count > 1:
            summary = f"{realtime:%H:%M:%S}:{transport} Burst of {burst_count} messages, first was..."
        else:
            summary = f"{realtime:%H:%M:%S}:{transport} {entry['MESSAGE'] if 'SYSLOG_IDENTIFIER' not in entry else entry['SYSLOG_IDENTIFIER']}"
        print("summary=", summary)
        return summary


    def determine_message(self, entry):
        message = entry['MESSAGE']
        print(message)
        return f"{message}"

    def is_notable(self, entry):
        message = entry['MESSAGE']
        if message != "":
            for ignore_key, ignore_spec in self.config['IGNORE'].items():
                if ignore_spec in message:
                    print(f"Ignore option {ignore_key} ignoring: {message}")
                    return False
        return True

    def watch(self):
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
            burst_count = 0;
            first_notable = None
            while journal_reader_poll.poll(2000):
                if journal_reader.process() == journal.APPEND:
                    for entry in journal_reader:
                        burst_count += 1
                        if self.is_notable(entry):
                            if first_notable is None:
                                first_notable = entry
                        if first_notable:
                            print(f"count={burst_count} {entry['MESSAGE']}")
            if first_notable is not None:
                notify.notify_desktop(app_name=self.determine_app_name(first_notable),
                                      summary=self.determine_summary(first_notable, burst_count=burst_count),
                                      message=self.determine_message(first_notable))


# def looping():
#     notify = NotifyFreeDesktop()
#     j = journal.Reader()
#     j.seek_tail()
#     j.get_previous()
#     while True:
#         j_state = j.wait(-1)
#         if j_state == journal.APPEND:
#             count = 1
#             last_app_name = None
#             for entry in j:
#                 print(entry)
#                 if count == 1:
#                     last_app_name = determine_app_name(entry)
#                     notify.notify_desktop(app_name=last_app_name,
#                                           summary=determine_summary(entry),
#                                           message=entry['MESSAGE'])
#                 count += 1
#             if count > 1:
#                 notify.notify_desktop(app_name=last_app_name,
#                                       summary="End of a burst of messages",
#                                       message=f"The burst had {count} messages in total.")


def main():
    config = configparser.ConfigParser()
    config['IGNORE'] = {'kwin_bad_damage': 'XCB error: 152 (BadDamage)',
                        'kwin_bad_window': 'kwin_core: XCB error: 3 (BadWindow)',
                        'xyzzy': 'xyzzy',
                        'self_caused': 'NotificationPopup.',
                        'qt_kde_binding_loop': 'Binding loop detected for property'}
    j_watcher = JournalWatcher(config)
    j_watcher.watch()


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
