Summary:   A tool to convert documents from/to any format supported by LibreOffice
Name:      unoconv
Version:   master
Release:   1%{?dist}
License:   GPLv2
URL:       https://github.com/elemental-lf/unoconv

BuildArch: noarch

BuildRequires: asciidoc
BuildRequires: xmlto

Requires:  libreoffice-filters
Requires:  libreoffice-pyuno
Suggests:  libreoffice-writer2latex
Suggests:  openoffice.org-diafilter

%description
Universal Office Converter (unoconv) is a command line tool to convert any
document format that LibreOffice can import to any document format that
LibreOffice can export. It makes use of the LibreOffice's UNO bindings for
non-interactive conversion of documents.

Supported document formats include Open Document Format (.odg, .odp, .ods,
.odt), MS Word (.doc), MS Office Open/MS OOXML (.docx, .pptx, .xlsx), PDF,
HTML, RTF, and many more.

%define NVdir %{name}-%{version}
%prep
rm -rf %{NVdir}
git clone --branch %{version} --depth 1 %{url}.git %{NVdir}
rm %{NVdir}/doc/%{name}.1

%build
cd %{NVdir}
make %{?_smp_mflags}
asciidoc README.adoc

%install
cd %{NVdir}
make install DESTDIR="%{buildroot}"

%files
%doc %{NVdir}/AUTHORS %{NVdir}/ChangeLog %{NVdir}/README.html
%doc %{NVdir}/doc/errcode.html %{NVdir}/doc/filters.html %{NVdir}/doc/formats.html %{NVdir}/doc/selinux.html
%license %{NVdir}/COPYING
%{_mandir}/man1/%{name}.1*
%{_bindir}/%{name}

%changelog
