#
# spec file for package VM
# 

Name:           vm2
Summary:        The VM2 educational marketplace built on Flask and Firebird
Summary(ru):    Учебный маркетплейс VM2 на Flask и Firebird
URL:            https://example.local/vm2
License:        MIT

Epoch:          0
Version:        1.0.0
Release:        1%{?dist}

Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

Requires:       firebird >= 4.0
Requires:       firebird-utils
Requires:       python3
Requires:       python3-pip
Requires:       systemd
Requires:       shadow-utils


%description
VM2 is a learning marketplace built on Flask and Firebird.
There are three roles: buyer, seller, and moderator.
The package contains an application, a systemd service,
and a script for automatically creating a Firebird database.


%description -l ru
VM2 — учебный маркетплейс на Flask и Firebird.
Три роли: покупатель, продавец и модератор.
Пакет содержит приложение, systemd-сервис и скрипт
автоматического создания базы данных Firebird.


%prep
%setup -q


%conf


%build


%install
%{__install} -d %{buildroot}/opt/vm2

for item in app.py db.py requirements.txt routes templates static sql; do
    %{__cp} -r "${item}" %{buildroot}/opt/vm2/
done

%{__install} -Dpm 0755 packaging/vm2-init-db.sh \
    %{buildroot}%{_libexecdir}/vm2/vm2-init-db
%{__install} -Dpm 0644 packaging/vm2.service \
    %{buildroot}%{_unitdir}/vm2.service
%{__install} -Dpm 0644 packaging/vm2.sysconfig \
    %{buildroot}%{_sysconfdir}/sysconfig/vm2


%pre
getent group vm2 >/dev/null 2>&1 || \
    %{_sbindir}/groupadd -r vm2 || :
getent passwd vm2 >/dev/null 2>&1 || \
    %{_sbindir}/useradd -r -g vm2 -d /opt/vm2 -s /sbin/nologin \
    -c "VM2 marketplace service" vm2 || :


%post
%systemd_post vm2.service

VENV=/opt/vm2/venv
VENV_ERROR=0

if [ ! -x "${VENV}/bin/python" ]; then
    %{__echo} "[vm2] Создание виртуального окружения ${VENV}"
    if ! python3 -m venv "${VENV}"; then
        %{__echo} "[vm2] ОШИБКА: не удалось создать venv." >&2
        VENV_ERROR=1
    fi
fi

if [ -x "${VENV}/bin/python" ]; then
    if ! "${VENV}/bin/pip" install -r /opt/vm2/requirements.txt; then
        %{__echo} "[vm2] ОШИБКА: не удалось установить Python-зависимости." >&2
        VENV_ERROR=1
    fi
fi

%{__chown} -R vm2:vm2 "${VENV}" 2>/dev/null || :


DB_ERROR=0

if [ -r /etc/sysconfig/vm2 ]; then
    . /etc/sysconfig/vm2
fi

if ! /usr/libexec/vm2/vm2-init-db; then
    %{__echo} "[vm2] ОШИБКА: не удалось создать базу данных." >&2
    %{__echo} "[vm2] Проверьте /etc/sysconfig/vm2 и журнал установки." >&2
    DB_ERROR=1
fi

if [ "${VENV_ERROR}" -ne 0 ] || [ "${DB_ERROR}" -ne 0 ]; then
    exit 1
fi


%preun
%systemd_preun vm2.service


%postun
%systemd_postun_with_restart vm2.service

if [ "$1" -eq 0 ]; then
    %{__echo} "[vm2] База данных Firebird сохранена:"
    %{__echo} "[vm2]   /var/lib/vm2/vm2.fdb"
    %{__echo} "[vm2] Удалите её вручную, если она больше не нужна."
fi


%files
%doc README.md

%dir /opt/vm2
/opt/vm2/app.py
/opt/vm2/db.py
/opt/vm2/requirements.txt
/opt/vm2/routes/*
/opt/vm2/sql/*.sql
/opt/vm2/templates/*.html
/opt/vm2/templates/moderator/*.html
/opt/vm2/static/css/*
/opt/vm2/static/images/*
%attr(0775,vm2,vm2) %dir /opt/vm2/static/images

%{_libexecdir}/vm2/vm2-init-db
%{_unitdir}/vm2.service
%config(noreplace) %{_sysconfdir}/sysconfig/vm2

%changelog
* Fri Nov 13 2026 Vasiliy Makhov <vasiliy.makhov@red-soft.ru> - 0:1.0.0-1
- Initial build