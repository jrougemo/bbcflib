# General Modules #
import os, re

# Specific Modules #
from ..track import Track

# Specific Variables #
from ..track.test_variables import parser_tests, yeast_chr_file

###################################################################################
def run(create_sql_files=False):
    # Nice color output #
    def message(path, name, status, expected, extra=None):
        if extra: extra = re.sub(" '" + path + "'", "", extra)
        title, extension = name.split('.')
        def ext_to_clr(ext): return str({'bed':6,'wig':4,'gff':5}[ext])
        if expected: s = ('\033[1;37;4'+ ext_to_clr(extension) + 'm' + extension + '\033[0m' + ': ' + title).ljust(38)
        else:        s = ('\033[1;30;4'+ ext_to_clr(extension) + 'm' + extension + '\033[0m' + ': ' + title).ljust(38) 
        if status==expected:
            s += '\033[0;37m\033[42m passed the test \033[0m'
            if extra: s += ' \033[2;37m' + extra + '\033[0m'
        else:
            s += '\033[1;37m\033[41m\033[5;37m failed the test \033[0m'
            if extra: s += ' \033[1;33m' + extra + '\033[0m' 
        print s
    # Main loop #
    for path, expected in parser_tests:
        name = path.split('/')[-1]
        dir  = '/'.join(path.split('/')[:-1]) + '/'
        dest = dir + name.split('.')[0] + '.sql'
        if os.path.exists(dest): os.remove(dest) 
        try:
            with Track(path, name=name, chrfile=yeast_chr_file) as t:
                if create_sql_files: t.convert(dest)
        except Exception as err:
            message(path, name, False, expected, str(err))
            continue
        message(path, name, True, expected)

#-----------------------------------------#
# This code was written by Lucas Sinclair #
# lucas.sinclair@epfl.ch                  #
#-----------------------------------------#