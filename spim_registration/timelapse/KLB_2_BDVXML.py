#!/usr/bin/env python3

import xmltodict
import sys
from optparse import OptionParser
import os
from collections import OrderedDict
import pyklb


parser = OptionParser()
parser.add_option("-b", "--basedir", dest="basedir", type="string",
                  help="[REQUIRED] KLB file root folder")
parser.add_option("-r", "--res", dest="res", type="string",
                  help="[OPTIONAL] pixel resolution of axes in um comma separated: x_res,y_res,z_res")
parser.add_option("-o", "--output", dest="outpath", type="string",
                  help="[REQUIRED] mamut XML output file path")

(options, args) = parser.parse_args()

if options.res:
    res = [float(r) for r in options.res.split(',')]
else:
    res = [1.0, 1.0, 1.0]

# First we need to get the files and organize them by ViewSetup
root = os.listdir(options.basedir)

spms = [spm for spm in root if 'SPM' in spm]
tms = [tm for tm in os.listdir(os.path.join(options.basedir, spms[0])) if 'TM' in tm]
chms = [chm for chm in os.listdir(os.path.join(options.basedir, spms[0], tms[0])) if 'CM' in chm and '.klb' in chm]
cms = []
chs = []

for el in chms:
    s = el.strip().split('_')
    cm = [i for i in s if 'CM' in i][0]
    ch = [i for i in s if 'CH' in i][0].split('.')[0]
    if cm not in cms:
        cms.append(cm)
    if ch not in chs:
        chs.append(ch)

# Checking that all the files are here !
error = False
for spm in spms:
    for tm in tms:
        for cm in cms:
            for ch in chs:
                path = os.path.join(options.basedir, spm, tm, "{}_{}_{}_{}.klb".format(spm, tm, cm, ch))
                if not os.path.isfile(path):
                    print("File is missing:", path)
                    error =True
if error:
    print("Error during file checking... Some files are missing... Exiting")
    sys.exit(1)

last_tm = sorted(tms)[-1]

# Define the XML
templates = []
viewsetups = []

id = 0
s = 0
for spm in spms:
    c = 0
    for cm in cms:
        h = 0
        for ch in chs:
            path = os.path.join(options.basedir, spm, last_tm, "{}_{}_{}_{}.klb".format(spm, last_tm, cm, ch))
            template = OrderedDict([('template',
                                           path),
                                          ('timeTag', 'TM')])
            headers = pyklb.readheader(path)
            dims = headers['imagesize_tczyx'][2:]
            viewsetup = OrderedDict([('id', str(id)),
                      ('name', str(id)),
                      ('size', '{} {} {}'.format(dims[2], dims[1], dims[0])),
                      ('voxelSize',
                       OrderedDict([('unit', 'µm'), ('size', '{} {} {}'.format(res[0], res[1], res[2]))])),
                      ('attributes',
                       OrderedDict([('illumination', '0'),
                                    ('channel', str(h)),
                                    ('tile', str(s)),
                                    ('angle', str(c))]))])
            templates.append(template)
            viewsetups.append(viewsetup)
            h += 1
            id += 1
        c += 1
    s += 1

# Making the attributes part
attr = []
attr.append(OrderedDict([('@name', 'illumination'),
              ('Illumination', OrderedDict([('id', '0'), ('name', '0')]))]))
channels =  OrderedDict([('@name', 'channel'),
              ('Channel', [])])
for ch in range(len(chs)):
    channels['Channel'].append(OrderedDict([('id', '{}'.format(ch)), ('name', '{}'.format(ch))]))

attr.append(channels)

tiles = OrderedDict([('@name', 'tile'),
             ('Tile',
              [])])
for spm in range(len(spms)):
    tiles['Tile'].append(OrderedDict([('id', '{}'.format(spm)), ('name', '{}'.format(spm))]))

attr.append(tiles)

angles = OrderedDict([('@name', 'angle'),
             ('Angle',[])])

for cm in range(len(cms)):
    angles['Angle'].append(OrderedDict([('id', '{}'.format(cm)), ('name', '{}'.format(cm))]))

attr.append(angles)

registrations = []
for tm in range(len(tms)):
    for s in range(len(viewsetups)):
        registration = OrderedDict([('@timepoint', str(tm)),
                                       ('@setup', str(s)),
                                       ('ViewTransform',
                                        OrderedDict([('@type',
                                                      'affine'),
                                                     ('affine',
                                                      '1.0 0.0 0.0 0.0 0.0 1.0 0.0 0.0 0.0 0.0 {} 0.0'.format(res[2]/res[0]))]))])
        registrations.append(registration)


XML =OrderedDict([('SpimData',
              OrderedDict([('@version', '0.2'),
                           ('BasePath',
                            OrderedDict([('@type', 'relative'),
                                         ('#text', '.')])),
                           ('SequenceDescription',
                            OrderedDict([('ImageLoader',
                                          OrderedDict([('@format', 'klb'),
                                                       ('Resolver',
                                                        OrderedDict([('@type',
                                                                      'org.janelia.simview.klb.bdv.KlbPartitionResolver'),
                                                                     ('ViewSetupTemplate', templates
                                                                      )]))])),
                                         ('ViewSetups',
                                          OrderedDict([('ViewSetup', viewsetups ),
                                                       ('Attributes', attr
                                                        )])),
                                         ('Timepoints',
                                          OrderedDict([('@type', 'range'),
                                                       ('first', '0'),
                                                       ('last', '{}'.format(len(tms)))]))])),
                           ('ViewRegistrations',
                            OrderedDict([('ViewRegistration', registrations)]))
                  ])
              )])

out = xmltodict.unparse(XML, pretty=True)
f = open(options.outpath, 'w')
f.write(out)
f.close()
