#!/usr/bin/env python
#
# $Id: setup.py,v 1.25 2009/11/30 22:40:05 ghantoos Exp $
#
#    Copyright (C) 2008-2009  Ignace Mouzannar (ghantoos) <ghantoos@ghantoos.org>
#
#    This file is part of lshell
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from distutils.core import setup

if __name__ == '__main__':

    setup(name='arte+7recorder',
        version='5.0.0',
        description='Limited Shell',
        long_description="""Limited Shell (lshell) is lets you restrict the \
environment of any user. It provides an easily configurable shell: just \
choose a list of allowed commands for every limited account.""",
        author='Adrien Beudin (beudbeud)',
        author_email='beudbeud@gmail.com',
        maintainer='Adrien Beudin (beudbeud)',
        maintainer_email='beudbeud@gmail.com',
        url='https://launchpad.net/arte+7recorder',
        license='GPL',
        scripts = ['bin/arte7recorder'],
        data_files = [('share/arte7recorder/doc',['README', 'COPYING', 'ChangeLog']),
		('share/applications/',['arte+7recorder.desktop']),
		('share/pyshared/arte7recorder',['arte7recorder/arte7recorder.py',
							   	'arte7recorder/Catalog.py',
								'arte7recorder/Arte7recorderWindow.ui',
								'arte7recorder/__init__.py',
								'arte7recorder/icon.png']),
		('share/pyshared/arte7recorder/locale/fr_FR/LC_MESSAGES/',['arte7recorder/locale/fr_FR/LC_MESSAGES/messages.mo',
								'arte7recorder/locale/fr_FR/LC_MESSAGES/messages.po']),
		('share/pixmaps/',['arte-icon.png'])],
    )
