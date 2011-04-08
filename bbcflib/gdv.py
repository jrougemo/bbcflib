"""
===============
bbcflib.gdv
===============

Python API for the GDV genome viewer.
"""
import urllib, urllib2
import json
############ GDV requests ############
                                                                                                                                  
def create_gdv_project( gdv_key, gdv_email,
                        name, run_key, nr_assembly_id,
                        gdv_url="http://svitsrv25.epfl.ch/gdv", public=False ):
    '''
    Create a new project on GDV interface
    :param gdv_email: your login in TEQUILA
    :param gdv_key: your user key (get it from your GDV account)
    :param rn_assembly_id: the nrAssembly identifier of the species in Genrep
    :param name: name of the project
    :param public: 'true' to make the project public -optionnal-
    :rtype: a json : {'project_id':<the id>,'public_url':<the public url>} or {'project_id':<the id>} if you didn't make the 
    project public 
    '''
    request = { "id": "gdv_post", 
                "mail": gdv_email,
                "key": gdv_key, 
                "command": "new_project",
                "name": str(name),
                "seq_id": str(nr_assembly_id),
                "public": str(public).lower() }
    return json.load(urllib2.urlopen( gdv_url+"/post", urllib.urlencode(request))) 

def get_project_id(json):
    return json['project_id']
def get_public_url(json):
    return json['public_url']

def add_gdv_track( gdv_key, gdv_email,
                   project_id,
                   url,
                   name=None,
                   gdv_url="http://svitsrv25.epfl.ch/gdv" ):
    '''
    Add a new track on a project on GDV
    :param gdv_email: your login in TEQUILA
    :param gdv_key: your user key (get it from your GDV account)
    :param name: name of the track -optionnal- (will take the file name by default)
    :param project_id: the project id to add the track
    :param url : the URL where to fetch the file
    '''
    request = { "id": "gdv_post",
                "mail": gdv_email,
                "key": gdv_key,
                "command": "add_track",
                "project_id": str(project_id),
                "url": str(url) }
    if name != None: 
        request['name']=name
    return urllib2.urlopen( gdv_url+"/post", urllib.urlencode(request) ).read()
    
def add_gdv_sqlite( gdv_key, gdv_email,
                    project_id,
                    url,
                    name=None,
                    gdv_url="http://svitsrv25.epfl.ch/gdv",
                    datatype="quantitative" ):
    '''
    Add a new track on a project on GDV
    :param gdv_email: your login in TEQUILA
    :param gdv_key: your user key (get it from your GDV account)
    :param name: name of the track -optionnal- (will take the file name by default)
    :param project_id: the project id to add the track
    :param url : the URL where to fetch the file
    '''
    request = { "id": "gdv_post",
                "mail": gdv_email,
                "key": gdv_key,
                "command": "add_sqlite",
                "project_id": str(project_id),
                "url": str(url),
                "datatype": datatype }
    if name != None: 
        request['name'] = name
    return urllib2.urlopen( gdv_url+"/post", urllib.urlencode(request)).read()


def add_sql_files( gdv_key, gdv_email,
                   project_id,
                   files, names,
                   serv_url="http://htsstation.vital-it.ch/chipseq",
                   gdv_url="http://svitsrv25.epfl.ch/gdv",
                   datatype="quantitative" ):
    return [add_gdv_sqlite(gdv_key,gdv_email,project_id,
                           serv_url+"/get_file?name="+f, names[i],
                           gdv_url,dataype) 
            for i,f in enumerate(files)]

############################################################     
