Name:		signal-desktop
Version:	1.30.0
Release:	1%{?dist}
Summary:	Private messaging from your desktop
License:	GPLv3
URL:		https://github.com/signalapp/Signal-Desktop/

Source0:	https://github.com/signalapp/Signal-Desktop/archive/v%{version}.tar.gz
Source1:        vendor.tar.xz

#ExclusiveArch:	x86_64
BuildRequires: binutils, git, python2, gcc, gcc-c++, yarn, openssl-devel, bsdtar, jq
BuildRequires: nodejs, ca-certificates, libxcrypt-compat

Requires:   GConf2, libnotify, libappindicator, libXtst, nss

%description
Private messaging from your desktop

# Steps to build vendor.tar.xz
# cd Signal-Desktop/
# yarn install --pure-lockfile --verbose
# pushd node_modules/protobufjs/cli
# npm --silent install espree@^3.5.3 chalk@^1.1.3 uglify-js@^2.8.2
# popd
# pushd node_modules/@journeyapps/sqlcipher
# npm install --prefer-offline
# popd
# rm ../vendor.tar.xz; XZ_OPT="-T8" tar cJf ../vendor.tar.xz node_modules

%prep
pwd
rm -rf Signal-Desktop-%{version}
tar xfz %{S:0}
tar xf %{S:1} -C Signal-Desktop-%{version}/
cd Signal-Desktop-%{version}

# allow node 10
# sed -i 's/"node": "^8.9.3"/"node": ">=8.9.3"/' package.json

# + avoid using fedora's node-gyp
#yarn --no-default-rc add --dev node-gyp

%build
cd Signal-Desktop-%{version}

node --version

# avoid using fedora's node-gyp
# npm install node-gyp

# Allow higher node versions
sed -i 's/"node": "/&>=/' package.json

# yarn install
yarn --offline icon-gen

# use dynamic linking
patch --no-backup-if-mismatch -Np1 << 'EOF'
--- a/node_modules/@journeyapps/sqlcipher/deps/sqlite3.gyp	2019-01-22 21:59:46.974203280 +0100
+++ b/node_modules/@journeyapps/sqlcipher/deps/sqlite3.gyp	2019-01-22 23:05:52.257819994 +0100
@@ -64,16 +64,14 @@
         },
         'link_settings': {
           'libraries': [
-            # This statically links libcrypto, whereas -lcrypto would dynamically link it
-            '<(SHARED_INTERMEDIATE_DIR)/sqlcipher-amalgamation-<@(sqlite_version)/OpenSSL-macOS/libcrypto.a'
+            '-lcrypto'
           ]
         }
       },
       { # Linux
         'link_settings': {
           'libraries': [
-            # This statically links libcrypto, whereas -lcrypto would dynamically link it
-            '<(SHARED_INTERMEDIATE_DIR)/sqlcipher-amalgamation-<@(sqlite_version)/OpenSSL-Linux/libcrypto.a'
+            '-lcrypto'
           ]
         }
       }]
@@ -140,8 +138,7 @@
         { # linux
           'include_dirs': [
             '<(SHARED_INTERMEDIATE_DIR)/sqlcipher-amalgamation-<@(sqlite_version)/',
-            '<(SHARED_INTERMEDIATE_DIR)/sqlcipher-amalgamation-<@(sqlite_version)/openssl-include/'
-          ]
+            ]
         }]
       ],
EOF

# build assets (icons), then RPM - building a plain directory loses the later install paths
# yarn --offline --no-default-rc generate --force --ignore-engines
yarn grunt exec:build-protobuf exec:transpile concat copy:deps sass

#env SIGNAL_ENV=production yarn --offline --no-default-rc --verbose build-release --linux rpm
SIGNAL_ENV=production \
yarn electron-builder \
    --config.extraMetadata.environment=$SIGNAL_ENV \
    --config.directories.output=release \
    --linux tar.xz

%install

# Electron directory of the final build depends on the arch
%ifnarch x86_64
    %global PACKDIR linux-ia32-unpacked
%else
    %global PACKDIR linux-unpacked
%endif

# %{_builddir}/Signal-Desktop-%{version}/release/linux-unpacked/*
bsdtar xf %{_builddir}/Signal-Desktop-%{version}/release/signal-desktop-*.rpm -C %{buildroot}


# create symlink
install -dm755 %{buildroot}%{_bindir}/
ln -s /opt/Signal/signal-desktop %{buildroot}%{_bindir}/signal-desktop

cat %{buildroot}//usr/share/applications/signal-desktop.desktop

# Changes from upstream:
# 1. Run signal WITH sandbox since it looks like there's no problems with fedora and friends
# 2. Use tray icon by default
# 3. Small fix for tray for Plasma users
patch --no-backup-if-mismatch -p0 %{buildroot}//usr/share/applications/signal-desktop.desktop<<'EOF'
4c4
< Exec=/opt/Signal/signal-desktop --no-sandbox %U
---
> Exec=env XDG_CURRENT_DESKTOP=Unity /usr/bin/signal-desktop --use-tray-icon %U
EOF

%files
%defattr(-,root,root)
/usr/share/icons/hicolor/*/apps/signal-desktop.png
/usr/share/applications/signal-desktop.desktop
/opt/Signal
%{_bindir}/signal-desktop


%changelog
* Thu Nov 14 2019 Guilherme Cardoso <gjc@ua.pt> 1.28.0-1
 - Simplify changelog to include only major changes

* Fri Sep 6 2019 Guilherme Cardoso <gjc@ua.pt> 1.27.1-1
 - Version bump
 - Small adjustments to rpm spec file and its patches

* Sat Mar 30 2019 Guilherme Cardoso <gjc@ua.pt> 1.23.2-1
  - Updated to dynamic eletron version, idea taken from
 ArchLinux AUR Signal package (_installed_electron_version)

* Thu Jan 17 2019 Guilherme Cardoso <gjc@ua.pt> 1.20.0-2
 - Version bump
 - Updated patches from archlinux aur build
 - Add depndencies for Fedora rawhide

* Wed Oct 31 2018 Guilherme Cardoso <gjc@ua.pt> 1.17.2-1
 - Version bump
 - Explicit nodejs dependency, which tries to solve the requirement of having nodejs LTS version 8
 - Thanks clime for the help

* Mon Oct 22 2018 Guilherme Cardoso <gjc@ua.pt> 1.16.3-4
 - Fix wrong this rpmspec version info

* Mon Oct 15 2018 Guilherme Cardoso <gjc@ua.pt> 1.16.2-3
  - Workaround for KDE plasma Signal's tray icon
  https://github.com/signalapp/Signal-Desktop/issues/1876

* Fri Oct 12 2018 Guilherme Cardoso <gjc@ua.pt> 1.16.2-2
  - Patch to use tray icon

* Fri Aug 17 2018 Guilherme Cardoso <gjc@ua.pt> 1.15.5-2
  - Try to patch to allow higher node versions for Fedora Rawhide
  - Manual symlink

* Thu Aug 16 2018 Matthias Andree <mandree@FreeBSD.org> 1.15.5-1
  - Shuffle things around a bit
  - Add jq to build requisites
  - tweak %files section so it actually finds its inputs
  - add node-gyp to developer dependencies only
  - add -no-default-rc to yarn calls throughout

* Tue Aug 14 2018 Guilherme Cardoso <gjc@ua.pt> 1.15.4-1
  - Version bump
  - Build fixes arround embebed OpenSSL's from mandree and stemid
  Link:
  https://github.com/signalapp/Signal-Desktop/issues/2634

* Wed May 02 2018 Guilherme Cardoso <gjc@ua.pt> 1.9.0-1
  - Version bump
  - Spec file cleanup

* Mon Apr 16 2018 Guilherme Cardoso <gjc@ua.pt> 1.7.1-4
  - Added a few more yarn steps (check, lint)

* Mon Apr 16 2018 Guilherme Cardoso <gjc@ua.pt> 1.7.1-3
  - Fix build. Requires 'yarn transpile'. Thanks spacekookie.
  Ref: https://github.com/signalapp/Signal-Desktop/issues/2256

* Sat Apr 14 2018 Guilherme Cardoso <gjc@ua.pt> 1.7.1-2
  - Remove patch lowering nodejs due to async problems
  - Simplified BuildRequires

* Wed Apr 11 2018 Guilherme Cardoso <gjc@ua.pt> 1.6.1-2
  - Fix desktop shortcut (thanks to bol for reporting)

* Tue Mar 13 2018 Guilherme Cardoso <gjc@ua.pt> 1.6.0-1
  - Version bump
  - Update project homepage url
  - Patch to override nodejs version of Signal's sources

* Sun Feb 18 2018 Guilherme Cardoso <gjc@ua.pt> 1.3.0-2
  - Build from sources instead of unpacking .deb release

* Mon Feb 05 2018 Guilherme Cardoso <gjc@ua.pt> 1.3.0-1
  - Version bump
  - Added missing dependencies from original deb package

* Thu Nov 02 2017 Richard Monk <richardmonk@gmail.com> 1.0.35-1
  - Initial Packaging
