#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Author: Guillermo Robles
#
# Extract data from the register file

import csv
import re
import sqlite3


def remove_tildes(string):
    """Removes tildes. Nothing more to say
    """
    return string.replace('á', 'a')\
                 .replace('é', 'e')\
                 .replace('í', 'i')\
                 .replace('ó', 'o')\
                 .replace('ú', 'u')\
                 .replace('Á', 'A')\
                 .replace('É', 'E')\
                 .replace('Í', 'I')\
                 .replace('Ó', 'O')\
                 .replace('Ú', 'U')


def generate_name_permutations(name):
    """Some people has the surnames before the name, some after. Generate
    multiple permutations of the name to fix it.
    """
    a = name.split(' ')
    return [' '.join(a),
            ' '.join(a[-1:]+a[:-1]),
            ' '.join(a[-2:]+a[:-2]),
            ' '.join(a[-3:]+a[:-3])]


# Load DB connection
conn = sqlite3.connect('humans.db')
c = conn.cursor()

# Load Schema
schema = open('schema.sql', 'r').read()
c.executescript(schema)
conn.commit()

# Load subjects
subject = open('sources/subject', 'rb')
subject_dict = {}
for i in subject.readlines():
    code = i.split(':')[0]
    name = remove_tildes(i).split(':')[1].replace('\n', '')
    subject_dict[code] = name
    c.execute("INSERT INTO SUBJECT (code,name) VALUES ('{}','{}');"
              .format(code, name))
conn.commit()

# Load census info
census = open('sources/student.csv', 'rb')
census_dict = {}
bachelor_array = []
bachelor_dict = {}
census_reader = csv.reader(census, delimiter=',', quotechar='"')
for i in census_reader:
    dni = i[0].strip()
    name = i[1].strip()
    bachelor = i[2].strip()
    census_dict[name.upper()] = {"dni": dni, "bachelor": bachelor}
    bachelor_array.append(bachelor)

# Load Bachelors
bachelor_index = 1
bachelor_dict = {'UNKNOWN': 0}
c.execute("INSERT INTO BACHELOR (code,name) VALUES ('{}','{}');"
          .format(0, 'UNKNOWN'))
for i in list(set(bachelor_array)):
    bachelor_dict[i] = bachelor_index
    c.execute("INSERT INTO BACHELOR (code,name) VALUES ('{}','{}');"
              .format(bachelor_index, i))
    bachelor_index += 1
conn.commit()

# Load student NIPs
hendrix = open('sources/passwd', 'rb')
hendrix_dict = {}
hendrix_reader = csv.reader(hendrix, delimiter=':', quotechar='"')
for i in hendrix_reader:
    if re.match('a[0-9]{6}', i[0]):
        nip = i[0].replace('a', '')
        nombre = i[4].upper()
        hendrix_dict[nombre] = nip

# Create relationship between NIPs and DNIs
students_dict = {}
for i in census_dict:
    students_dict[i] = census_dict[i]

for i in hendrix_dict:
    perm = generate_name_permutations(i)
    inserted = False
    for j in range(0, 4):
        if perm[j] in census_dict:
            students_dict[perm[j]]['nip'] = hendrix_dict[i]
            inserted = True
    if not inserted:
        students_dict[i] = {'nip': hendrix_dict[i], 'dni': '', 'bachelor': ''}

# Load student/bachelor registrations info into DB
nip_falso = 0
for i in students_dict:
    name = i
    try:
        bachelor = bachelor_dict[students_dict[i]['bachelor']]
    except KeyError:
        bachelor = 0
    dni = students_dict[i]['dni']

    if 'nip' in students_dict[i]:
        nip = students_dict[i]['nip']
    else:
        nip = nip_falso
        nip_falso += 1
    c.execute("INSERT INTO STUDENT (nip,dni,name) VALUES ('{}','{}','{}');"
              .format(nip, dni, name))
    c.execute("INSERT INTO REGISTER (nip,code) VALUES ('{}','{}');"
              .format(nip, bachelor))
conn.commit()

# Load enrollments
enrollment = open('sources/group', 'rb')
enrollment_dict = {}
for i in enrollment.readlines():
    code = i.split(':')[0].replace('g', '')
    students = [j.replace('\n', '').replace('a', '')
                for j in i.split(':')[3].split(',')]
    if students[0] == '':
        students = []
    if re.match('[0-9]{5}', code):
        enrollment_dict[code] = students
        for j in students:
            c.execute("INSERT INTO ENROLLMENT (nip,code) VALUES ('{}','{}');"
                      .format(j, code))
conn.commit()

# The end
c.close()
conn.close()
