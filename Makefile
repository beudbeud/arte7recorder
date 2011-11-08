# $Id: Makefile,v 1.6 2009/12/02 22:09:35 beudbeud Exp $
#

PYTHON=`which python`
DESTDIR=/
BUILDIR=$(CURDIR)/debian/arte7recorder
PROJECT=arte+7recorder
VERSION=5.0.0

all:
	@echo "make source - Create source package"
	@echo "make install - Install on local system"
	@echo "make builddeb - Generate a deb package"
	@echo "make clean - Get rid of scratch and byte files"
	@echo "make uninstall - Uninstall"

source:
	$(PYTHON) setup.py sdist $(COMPILE)

install:
	$(PYTHON) setup.py install --root $(DESTDIR) $(COMPILE) --prefix=/usr --record files.txt

builddeb:
	# build the source package in the parent directory
	# then rename it to project_version.orig.tar.gz
	$(PYTHON) setup.py sdist $(COMPILE) --dist-dir=../ --prune
	rename -f 's/$(PROJECT)-(.*)\.tar\.gz/$(PROJECT)_$$1\.orig\.tar\.gz/' ../*
	# build the package
	dpkg-buildpackage -i -I -rfakeroot

clean:
	$(PYTHON) setup.py clean
	$(MAKE) -f $(CURDIR)/debian/rules clean
	rm -rf build/ MANIFEST
	find . -name '*.pyc' -delete
	rm files.txt

uninstall:
	sed -i 's/usr/\/usr/g' files.txt
	cat files.txt | xargs rm
	sed -i 's/\/usr/usr/g' files.txt
