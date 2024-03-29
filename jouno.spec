#
# spec file for vducontrols
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, version 3.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Contact:  m i c h a e l   @   a c t r i x   .   g e n   .   n z
#

Name: jouno
Version: 1.3.6
Release: 0
License: GPL-3.0-or-later
BuildArch: noarch
URL: https://github.com/digitaltrails/jouno
Group: System/GUI/Other
Summary: A GUI Systemd-Journal monitor with DBUS Notification forwarding
Source0:        %{name}-%{version}.tar.gz

%if 0%{?suse_version} || 0%{?fedora_version}
Requires: python3 python3-qt5 python3-dbus-python python3-systemd
%endif

BuildRequires: coreutils

BuildRoot: %{_tmppath}/%{name}-%{version}-build
%description
Jouno is a GUI Systemd-Journal monitoring and viewing tool.  Jouno can filter and
bundle messages for forwarding to the desktop as standard DBUS Freedesktop Notifications
(most linux desktop environments present DBUS Notifications as popup messages).

%prep
%setup -q

%build

exit 0

%install
mkdir -p %{buildroot}/%{_bindir}
mkdir -p %{buildroot}/%{_datadir}/applications
mkdir -p %{buildroot}/%{_datadir}/icons/hicolor/64x64/apps
install -m 755 jouno.py  %{buildroot}/%{_bindir}/%{name}

cat > %{name}.desktop <<'EOF'
[Desktop Entry]
Type=Application
Terminal=false
Exec=%{_bindir}/%{name}
Name=Jouno
GenericName=Jouno
Comment=A Systemd-Journal to Freedesktop-Notifications forwarder.
Icon=jouno
Categories=Qt;System;Monitor;System;
EOF

install -m644 %{name}.desktop %{buildroot}/%{_datadir}/applications
install -m644 %{name}.png %{buildroot}/%{_datadir}/icons/hicolor/64x64/apps

#gzip -c docs/_build/man/vdu_controls.1 > %{buildroot}/%{_datadir}/man/man1/%{name}.1.gz

%post


%files
%dir %{_datadir}/icons/hicolor
%dir %{_datadir}/icons/hicolor/*
%dir %{_datadir}/icons/hicolor/*/apps
%license LICENSE.md
%defattr(-,root,root)
%{_bindir}/%{name}
%{_datadir}/applications/%{name}.desktop
%{_datadir}/icons/hicolor/64x64/apps/%{name}.png

%changelog

* Mon Mar 11 2024 Michael Hamilton <michael@actrix.gen.nz>
- Fix date comparison error in Journal-Query for newer python versions
* Fri Dec 29 2023 Michael Hamilton <michael@actrix.gen.nz>
- Add Setting Dark Tray Enabled for themes such as Breeze Twilight
* Mon Oct 24 2022 Michael Hamilton <michael@actrix.gen.nz>
- Recover from dbus reinit/desktop-error: jouno 1.3.4
* Mon Jul 18 2022 Michael Hamilton <michael@actrix.gen.nz>
- Usability improvements: jouno 1.3.3
* Mon Jul 18 2022 Michael Hamilton <michael@actrix.gen.nz>
- Usability improvements: jouno 1.3.2
* Wed Apr 13 2022 Michael Hamilton <michael@actrix.gen.nz>
- Wayland Fixes.  HiDPI fixes.  Fix queries on trucated logs: jouno 1.3.2
* Sat Jan 22 2022 Michael Hamilton <michael@actrix.gen.nz>
- On new message, on scroll to new end if prior position was at end: jouno 1.3.1
* Tue Dec 28 2021 Michael Hamilton <michael@actrix.gen.nz>
- Implement forward_xorg_session_enabled, wayland porting: jouno 1.3.0
* Mon Dec 20 2021 Michael Hamilton <michael@actrix.gen.nz>
- More responsive incremental search, revised status bar timeouts: jouno 1.2.2
* Wed Dec 15 2021 Michael Hamilton <michael@actrix.gen.nz>
- Minor improvements: jouno 1.2.1
* Mon Dec 06 2021 Michael Hamilton <michael@actrix.gen.nz>
- Journal query interface: jouno 1.2.0
* Sun Dec 05 2021 Michael Hamilton <michael@actrix.gen.nz>
- Faster incremental-search; case-insensitive incremental-search for lowercase patterns: jouno 1.1.3
* Sat Dec 04 2021 Michael Hamilton <michael@actrix.gen.nz>
- Detect if system tray is present, if not, ignore system_tray_enabled: jouno 1.1.2
* Fri Dec 03 2021 Michael Hamilton <michael@actrix.gen.nz>
- Faster startup by deferring UI scroll-to-bottom until old entries are read: jouno 1.1.1
* Fri Dec 03 2021 Michael Hamilton <michael@actrix.gen.nz>
- Add the ability to show past messages, ether n, or from last boot: jouno 1.1.0
* Thu Nov 18 2021 Michael Hamilton <michael@actrix.gen.nz>
- Default system-tray-enabled to false - some systems lack a system tray: jouno 1.0.7
* Tue Nov 09 2021 Michael Hamilton <michael@actrix.gen.nz>
- Show position when moving to the next/previous match: jouno 1.0.6
* Fri Nov 05 2021 Michael Hamilton <michael@actrix.gen.nz>
- Escape HTML before forwarding. Minor fixes and improvements: jouno 1.0.5
* Fri Nov 05 2021 Michael Hamilton <michael@actrix.gen.nz>
- Abandon Qt table edit-mode in favour of read-only+context-menu: jouno 1.0.4
* Thu Nov 04 2021 Michael Hamilton <michael@actrix.gen.nz>
- Added search to the Journal-Entry full-text panel: jouno 1.0.3
* Tue Nov 02 2021 Michael Hamilton <michael@actrix.gen.nz>
- Faster incremental search. More reexp search options: jouno 1.0.2
* Tue Nov 02 2021 Michael Hamilton <michael@actrix.gen.nz>
- Fixes for first time installation and use: jouno 1.0.1
* Sun Oct 24 2021 Michael Hamilton <michael@actrix.gen.nz>
- Packaged for rpm jouno 1.0.0
