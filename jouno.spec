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
Version: 1.0.0
Release: 0
License: GPL-3.0-or-later
BuildArch: noarch
URL: https://github.com/digitaltrails/jouno
Group: System/GUI/Other
Summary: A desktop tray app for forwarding systemd-Journal entries to Freedesktop-Notifications
Source0:        %{name}-%{version}.tar.gz

%if 0%{?suse_version} || 0%{?fedora_version}
Requires: python38 python38-qt5 python38-dbus-python python38-systemd
%endif

BuildRequires: coreutils

BuildRoot: %{_tmppath}/%{name}-%{version}-build
%description
jouno, is system-tray application for monitoring the systemd-journal. It raises
selected entries as desktop-notifications. The application monitors the
systemd-journal for new entries, filters them, and forwards them as standard
freedesktop dbus notifications.  Most linux desktops present these notifications
as popup messages.  Bursts of messages are handled by bundling them in to a
single summarising notification.

%prep
%setup -q

%build

exit 0

%install
mkdir -p %{buildroot}/%{_bindir}
mkdir -p %{buildroot}/%{_datadir}/applications
mkdir -p %{buildroot}/%{_datadir}/icons
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
install -m644 %{name}.png %{buildroot}/%{_datadir}/icons

#gzip -c docs/_build/man/vdu_controls.1 > %{buildroot}/%{_datadir}/man/man1/%{name}.1.gz

%post


%files
%license LICENSE.md
%defattr(-,root,root)
%{_bindir}/%{name}
%{_datadir}/applications/%{name}.desktop
%{_datadir}/icons/%{name}.png

%changelog

* Sun Oct 25 2021 Michael Hamilton <michael@actrix.gen.nz>
- Packaged for rpm
