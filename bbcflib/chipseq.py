"""
===============
bbcflib.chipseq
===============

This module provides functions to run a basic ChIP-seq analysis from reads mapped on
a reference genome.
The most important steps are the binding of ``macs`` via the 'add_macs_results' function, 
the peak deconvolution algorithm with the 'run_deconv' function and
the 'parallel_density_sql' function to create quantitative sql tracks from bam files. Below is the script used by the frontend::
    M = MiniLIMS( limspath )
    gl = use_pickle(M, "global variables")
    htss = frontend.Frontend( url=gl["hts_url"] )
    job = htss.job( hts_key )
    g_rep = genrep.GenRep( gl["genrep_url"], gl["bwt_root"] )
    with execution( M, description=hts_key, remote_working_directory=working_dir ) as ex:
        M_ms = MiniLIMS(ms_minilims)
        gl_ms = use_pickle(M_ms, "global variables")
        mapseq_url = gl_ms['hts_url']
        (processed, ms_job) = import_mapseq_results( job.options['mapseq_key'], M_ms, ex.working_directory, gl_ms["hts_url"] )
        g_rep_assembly = g_rep.assembly( ms_job.assembly_id )
        job.groups = ms_job.groups
        (p,g) = workflow_groups( ex, job, processed, g_rep_assembly.chromosomes, gl['script_path'] )

"""

import sqlite3
from bein import *
from bein.util import *
from bbcflib import frontend, mapseq
import pickle

############ gMiner operations ############
@program
def run_gMiner( job ):
    job_file = unique_filename_in()
    with open(job_file,'w') as f:
        pickle.dump(job,f)
    def get_output_files(p):
        with open(job_file,'r') as f:
            job = pickle.load(f)
        return job['job_output']
    return {"arguments": ["run_gminer.py",job_file], 
            "return_value": get_output_files}

def merge_sql( ex, sqls, names, description="merged.sql", outdir=None, via='lsf' ):
    """Run ``gMiner``'s 'merge_score' function on a set of sql files
    """
    if outdir == None: 
        outdir = unique_filename_in() 
    if not(os.path.exists(outdir)):
        os.mkdir(outdir)
    if not(isinstance(names,list)):
        names = []
    if len(names) < len(sqls):
        n = sqls
        n[:len(names)] = names
        names = n
    gMiner_job = dict([('track'+str(i+1),f) for i,f in enumerate(sqls)]
                      +[('track'+str(i+1)+'_name',str(ni)) 
                        for i,ni in enumerate(names)])
    gMiner_job['operation_type'] = 'genomic_manip'
    gMiner_job['manipulation'] = 'merge_scores'
    gMiner_job['output_location'] = outdir
    files = run_gMiner.nonblocking(ex,gMiner_job,via=via).wait()
    ex.add( files[0], description=description )
    return files[0]

############################################################

 
############ Peaks and annotation ############
@program
def macs( read_length, genome_size, bamfile, ctrlbam=None, shift=80, args=[] ):
    """Binding for the ``macs`` peak caller.

    takes one (optionally two) bam file(s) and
    the 'read_length', 'genome_size' and 'shift' parameters passed to ``macs``. 
    
    Returns the file prefix ('-n' option of ``macs``)
    """
    outname = unique_filename_in()
    macs_args = ["macs14","-t",bamfile]
    if ctrlbam != None:
        macs_args += ["-c",ctrlbam]
    macs_args += ["-n",outname,"-f","BAM",
                  "-g",str(genome_size),"-s",str(read_length)]
    if shift>0:
        macs_args += ["--shiftsize="+str(shift)]
    return {"arguments": macs_args+args, "return_value": outname}

def add_macs_results( ex, read_length, genome_size, bamfile,
                      ctrlbam=[None], name=None, shift=80, alias=None,
                      macs_args=[], via='lsf' ):
    """Calls the ``macs`` function on each possible pair 
    of test and control bam files and adds 
    the respective outputs to the execution repository.
    Returns the set of file prefixes.
    """
    if not(isinstance(bamfile,list)):
        bamfile = [bamfile]
    if not(isinstance(ctrlbam,list)):
        ctrlbam = [ctrlbam]
    futures = {}
    for i,bam in enumerate(bamfile):
        n = name['tests'][i]
        for j,cam in enumerate(ctrlbam):
            m = name['controls'][j]
            if m == None:
                nm = (n,)
            else:
                nm = (n,m)
            futures[nm] = macs.nonblocking( ex, read_length, genome_size, bam, 
                                            cam, shift, args=macs_args, via=via )
    prefixes = dict((n,f.wait()) for n,f in futures.iteritems())
    for n,p in prefixes.iteritems():
        description = "_vs_".join(n)
        touch( ex, p )
        ex.add( p, description="none:"+description, alias=alias )
        ex.add( p+"_peaks.xls", description="macs:"+description+"_peaks.xls",
                associate_to_filename=p, template='%s_peaks.xls' )
        ex.add( p+"_peaks.bed", description="macs:"+description+"_peaks.bed",
                associate_to_filename=p, template='%s_peaks.bed' )
        ex.add( p+"_summits.bed", description="macs:"+description+"_summits.bed",
                associate_to_filename=p, template='%s_summits.bed' )
        if len(n)>1:
            ex.add( p+"_negative_peaks.xls", description="macs:"+description+"_negative_peaks.xls",
                    associate_to_filename=p, template='%s_negative_peaks.xls' )
    return prefixes

@program
def sql_prepare_deconv(sql_dict,peaks_bed,chr_name,chr_length,cutoff,read_length):
    """Prepares files for the deconvolution algorithm.
    Calls the stand-alone ``sql_prepare_deconv.py`` script which needs 
    a directory of sql files (quantitative tracks for forward and reverse strand) 
    and a bed file (*_peaks.bed file from ``macs``) of wnriched regions to consider.
    Returns the name of an 'Rdata' file to be passed to the *R* deconvolution script.
    """
    out = unique_filename_in()
    args = [sql_dict['fwd'],sql_dict['rev'],peaks_bed,out,chr_name,
            str(chr_length),str(cutoff),str(read_length)]
    return {"arguments": ["sql_prepare_deconv.py"]+args, 
            "return_value": out}

@program
def run_deconv_r( counts_file, read_length, chr_name, script_path ):
    """Runs the 'deconv.R' script (found under 'script_path') on the 'counts_file' 
    input with parameters 'chr_name' (name of chromosome to process) and 'read_length'.
    Returns the pdf file and the 'Rdata' output. 
    """
    pdf_file = unique_filename_in()
    output_file = unique_filename_in()
    rargs = [counts_file, pdf_file, str(read_length), 
             chr_name, output_file, script_path]
    return {'arguments': ["R","--vanilla","--slave","-f",
                          os.path.join(script_path,"deconv.R"),
                          "--args"] + rargs,
            'return_value': {'pdf': pdf_file, 'rdata': output_file}}

@program
def sql_finish_deconv(sqlout,rdata):
    """Binds the ``sql_finish_deconv.py`` scripts which creates an sqlite file from
    'run_deconv''s output. 
    """
    return {"arguments": ["sql_finish_deconv.py",rdata,sqlout], 
            "return_value": sqlout}

def run_deconv(ex,sql,peaks,chromosomes,read_length,script_path, via='lsf'):
    """Runs the complete deconvolution process for a set of sql files and a bed file,
    parallelized over a set of chromosomes (a dictionary with keys 'chromosome_id' 
    and values a dictionary with chromosome names and lengths).
   
    Returns a dictionary of file outputs with keys file types 
    ('pdf', 'sql' and 'bed') and values the file names.
    """
    prep_futures = dict((c['name'],
                         sql_prepare_deconv.nonblocking( ex, sql, peaks, 
                                                         c['name'], c['length'],
                                                         1500, read_length, 
                                                         via=via ))
                        for c in chromosomes.values())
    rdeconv_futures = dict((c,
                            run_deconv_r.nonblocking( ex, f.wait(), read_length,
                                                      c, script_path, via=via ))
                           for c,f in prep_futures.iteritems())
    rdeconv_out = dict((c, f.wait()) for c,f in rdeconv_futures.iteritems())
    if len(rdeconv_out)>0:
        pdf_future = join_pdf.nonblocking( ex,
                                           [x['pdf'] for x in rdeconv_out.values()
                                            if x != None],
                                           via=via )
    sqlout = unique_filename_in()
    outfiles = {}
    conn = sqlite3.connect( sqlout )
    conn.execute('create table chrNames (name text, length integer)')
    conn.execute('create table attributes (key text, value text)')
    conn.execute('insert into attributes (key,value) values ("datatype","quantitative")')
    vals = [(v['name'],str(v['length'])) for v in chromosomes.values()]
    conn.executemany('insert into chrNames (name,length) values (?,?)',vals)
    [conn.execute('create table "'+v['name']+'" (start integer, end integer, score real)') 
     for v in chromosomes.values()]
    conn.commit()
    conn.close()
    for fout in rdeconv_out.values():
        if fout != None:
            f = sql_finish_deconv.nonblocking( ex, sqlout, fout['rdata'], via=via ).wait()
    outfiles['sql'] = sqlout
    outfiles['bed'] = sqlout+'_deconv.bed'
    if len(rdeconv_out)>0:
        outfiles['pdf'] = pdf_future.wait()
    else:
        outfiles['pdf'] = rdeconv_out.values()[0]['pdf']
    return outfiles
    
############################################################ 
@program
def wigToBigWig( sql ):
    """Binds ``wigToBigWig`` from the UCSC tools.
    """
    chrsizes = unique_filename_in()
    chromosomes = []
    connection = sqlite3.connect( sql )
    cur = connection.cursor()
    with open(chrsizes,'w') as f:
        cur = connection.cursor()
        cur.execute('select * from chrNames')
        connection.commit()
        for sql_row in cur:
            chromosomes.append(sql_row[0])
            f.write(' '.join([str(x) for x in sql_row])+"\n")
        cur.close()
    bedgraph = unique_filename_in()
    with open(bedgraph,'w') as f:
        for c in chromosomes:
            cur.execute('select * from "'+c+'"')
            connection.commit()
            for sql_row in cur:
                f.write("\t".join([c]+[str(x) for x in sql_row])+"\n")
            cur.close()
    bigwig = unique_filename_in()
    return {"arguments": ['wigToBigWig',bedgraph,chrsizes,bigwig], 
            "return_value": bigwig}

@program
def merge_two_bed(file1,file2):
    """Binds ``intersectBed`` from the 'BedTools' suite.
    """
    return {"arguments": ['intersectBed','-a',file1,'-b',file2], "return_value": None}

def merge_many_bed(ex,files,via='lsf'):
    """Runs ``intersectBed`` iteratively over a list of bed files.
    """
    out = files[0]
    for f in files[1:]:
        next = unique_filename_in()
        _ = merge_two_bed.nonblocking( ex, out, f, via=via, stdout=next ).wait()
        out = next
    return out

@program
def join_pdf(files):
    """Uses 'ghostscript' to join several pdf files into one.
    """
    out = unique_filename_in()
    gs_args = ['gs','-dBATCH','-dNOPAUSE','-q','-sDEVICE=pdfwrite',
               '-sOutputFile=%s'%out]
    gs_args += files
    return {"arguments": gs_args, "return_value": out}

def cat(files):
    """Concatenates files.
    """
    if len(files) > 1:
        out = unique_filename_in()
        with open(out,"w") as f1:
            for inf in files: 
                with open(inf,"r") as f2:
                    [f1.write(l) for l in f2]
                    f2.close()
            f1.close()
    elif len(files) == 1:
        out = files[0]
    else:
        out = None
    return out

@program
def bam_to_density( bamfile, chromosome_accession, chromosome_name, output,
                    nreads=1, merge=-1, read_length=-1, convert=True, sql=False,
                    args=[] ):
    """Runs the ``bam2wig`` program on a bam file and 
    normalizes for the total number of reads
    provided as argument 'nreads'. 

    Returns the name of the output wig or sql file(s) (if 'sql' is True).

    Use 'convert'=False if the bam already uses chromosome names instead of ids.
    """
    b2w_args = ["-w",str(nreads),"-s",bamfile,"-o",output]
    if convert:
        b2w_args += ["-a",chromosome_accession,"-n",chromosome_name]
    else:
        b2w_args += ["-a",chromosome_name]
    if merge>=0:
        b2w_args += ["-p",str(merge)]
    if read_length>0:
        b2w_args += ["-q",str(read_length)]
    if sql:
        b2w_args += ["-d"]
        if merge<0:
            files = [output+"fwd.sql",output+"rev.sql"]
        else:
            files = [output+"merged.sql"]
    else:
        if merge<0:
            b2w_args += ["-6"]
        files = output
    b2w_args += args
    return {"arguments": ["bam2wig"]+b2w_args, "return_value": files}

def compact_chromosome_name(key):
    if isinstance(key,str):
        return key
    elif isinstance(key,tuple) and len(key)>2:
        return str(key[0])+"_"+key[1]+"."+str(key[2])
    else:
        raise ValueError("Can't handle this chromosomes key ",key)

def parallel_density_wig( ex, bamfile, chromosomes, 
                          nreads=1, merge=-1, read_length=-1, convert=True, 
                          description="", alias=None, 
                          b2w_args=[], via='lsf' ):
    """Runs 'bam_to_density' in parallel 
    for every chromosome in the 'chromosomes' list with 'sql' set to False.
    Returns produces a single text wig file.
    """
    futures = [bam_to_density.nonblocking( ex, bamfile, compact_chromosome_name(k),
                                           v['name'], unique_filename_in(), nreads, merge, 
                                           read_length, convert, False, 
                                           args=b2w_args, via=via )
               for k,v in chromosomes.iteritems()]
    results = []
    for f in futures:
        try: 
            results.append(f.wait())
        except ProgramFailed:
            pass
    output = cat(results)
    ex.add( output, description=description, alias=alias )
    return output

def parallel_density_sql( ex, bamfile, chromosomes, 
                          nreads=1, merge=-1, read_length=-1, convert=True, 
                          description="", alias=None, b2w_args=[], via='lsf' ):
    """Runs 'bam_to_density' for every chromosome in the 'chromosomes' list.
    
    Returns one or two sqlite files depending 
    if 'merge'>=0 (shift and merge strands into one tracks) 
    or 'merge'<0 (keep seperate tracks for each strand).
    """
    output = unique_filename_in()
    touch(ex,output)
    if merge<0:
        suffix = ['fwd','rev']
    else:
        suffix = ['merged']
    for s in suffix:
        conn1 = sqlite3.connect( output+s+'.sql' )
        conn1.execute('create table chrNames (name text, length integer)')
        conn1.execute('create table attributes (key text, value text)')
        conn1.execute('insert into attributes (key,value) values ("datatype","quantitative")')
        vals = [(v['name'],str(v['length'])) for v in chromosomes.values()]
        conn1.executemany('insert into chrNames (name,length) values (?,?)',vals)
        [conn1.execute('create table "'+v['name']+'" (start integer, end integer, score real)') 
         for v in chromosomes.values()]
        conn1.commit()
        conn1.close()
    results = []
    for k,v in chromosomes.iteritems():
        future = bam_to_density.nonblocking( ex, bamfile, compact_chromosome_name(k),
                                             v['name'], output, nreads, merge,
                                             read_length, convert, True, 
                                             args=b2w_args, via=via )
        try: 
            results.append(future.wait())
        except ProgramFailed:
            pass
    ex.add( output, description='none:'+description+'.sql', alias=alias )
    [ex.add( output+s+'.sql', description='sql:'+description+'_'+s+'.sql',
             associate_to_filename=output, template='%s_'+s+'.sql' ) 
     for s in suffix]
    return dict((s,output+s+'.sql') for s in suffix)

###################### Workflow ####################

def workflow_groups( ex, job_or_dict, processed, chromosomes, script_path='', 
                     via='lsf' ):
    """Runs a chipseq workflow over bam files obtained by mapseq. Will optionally run ``macs`` and 'run_deconv'.
    
    Arguments are:

    * ``'ex'``: a 'bein' execution environment to run jobs in,
    
    * ``'job_or_dict'``: a 'Frontend' 'job' object, or a dictionary with key 'groups' and 'options' if applicable,
    
    * ``'chromosomes'``: a dictionary with keys 'chromosome_id' and values a dictionary with chromosome names and lengths,

    * ``'script_path'``: only needed if 'run_deconv' is in the job options, must point to the location of the R scripts.

    Defaults ``macs`` parameters (if not specified as a list in the job's options) are set as follows:

    * ``'--nomodel'``

    * ``'p'``: .001 (p-value threshold)

    * ``'bw'``: 200 ('bandwith')

    * ``'m'``: 3,60 ('minimum and maximum enrichments relative to background or control)

    Returns a tuple of a dictionary with keys *group_id* from the job groups, *macs* and *deconv* if applicable and values file description dictionaries and a dictionary of *group_ids* to *names* used in file descriptions.
"""
    gid2name = {}
    if isinstance(job_or_dict,frontend.Job):
        options = job_or_dict.options
        groups = job_or_dict.groups
    elif isinstance(job_or_dict,dict) and 'groups' in job_or_dict:
        if 'options' in job_or_dict:
            options = job_or_dict['options']
        groups = job_or_dict['groups']
    else:
        raise TypeError("job_or_dict must be a frontend.Job object or a dictionary with key 'groups'.")
    merge_strands = -1
    suffixes = ["fwd","rev"]
    if 'merge_strands' in options and options['merge_strands']>=0:
        merge_strands = options['merge_strands']
        suffixes = ["merged"]
    peak_calling = False
    if 'peak_calling' in options:
        peak_calling = options['peak_calling']
    peak_deconvolution = False
    if 'peak_deconvolution' in options:
        peak_deconvolution = options['peak_deconvolution']
    ucsc_bigwig = False
    if 'ucsc_bigwig' in options:
        ucsc_bigwig = options['ucsc_bigwig']
    b2w_args = []
    if 'b2w_args' in options:
        b2w_args = options['b2w_args']
    macs_args = ["--nomodel","-m","3,60","--bw=200","-p",".001"]
    if 'macs_args' in options:
        macs_args = options['macs_args']
    if not isinstance(processed,dict):
        raise TypeError("processed must be a dictionary.")
    for gid,group in groups.iteritems():
        if 'name' in group:
            group_name = re.sub(r'\s+','_',group['name'])
        else:
            group_name = gid
        gid2name[gid] = group_name
        mapped = processed[gid]
        if not isinstance(mapped,dict):
            raise TypeError("processed values must be dictionaries with keys *run_ids* or 'bam'.")
        if 'bam' in mapped:
            mapped = {'_': mapped}
        for k in mapped.keys():
            if not 'libname' in mapped[k]:
                mapped[k]['libname'] = group_name+"_"+str(k)
            if not 'stats' in mapped[k]:
                mapped[k]['stats'] = mapseq.bamstats( ex, mapped[k]["bam"] )
        if len(mapped)>1:
            wig = [parallel_density_sql( ex, m["bam"], chromosomes, 
                                         nreads=m["stats"]["total"], 
                                         merge=merge_strands, 
                                         convert=False, 
                                         description=m['libname'], 
                                         b2w_args=b2w_args, via=via ) 
                   for m in mapped.values()]
            merged_bam = merge_bam(ex, [m['bam'] for m in mapped.values()])
            ids = [m['libname'] for m in mapped.values()]
            merged_wig = dict((s, merge_sql(ex, [x[s] for x in wig], ids,
                                            description="sql:"+group_name+"_shift_"+s+".sql")) 
                              for s in suffixes)
        else:
            m = mapped.values()[0]
            merged_bam = m['bam']
            merged_wig = parallel_density_sql( ex, merged_bam, chromosomes, 
                                               nreads=m["stats"]["total"], 
                                               merge=merge_strands, 
                                               convert=False, 
                                               description=group_name, 
                                               b2w_args=b2w_args, via=via )
        processed[gid] = {'bam': merged_bam, 'wig': merged_wig,
                          'read_length': mapped.values()[0]['stats']['read_length'],
                          'genome_size': mapped.values()[0]['stats']['genome_size']}
        if ucsc_bigwig:
            bw_futures = [wigToBigWig.nonblocking( ex, merged_wig[s], via=via ) 
                          for s in suffixes]
            [ex.add(bw_futures[i].wait(),description='bigwig:'+group_name+'_'+s+'.bw')
             for i,s in enumerate(suffixes)]
    if peak_calling:
        tests = []
        controls = []
        names = {'tests': [], 'controls': []}
        wigs = {}
        for gid,group in processed.iteritems():
            if groups[gid]['control']:
                controls.append(group['bam'])
                names['controls'].append(gid2name[gid])
            else:
                tests.append(group['bam'])
                names['tests'].append(gid2name[gid])
                wigs[gid2name[gid]] = group['wig']
            read_length = group['read_length']
            genome_size = group['genome_size']
        if len(controls)<1:
            controls = [None]
            names['controls'] = [None]
        processed['macs'] = add_macs_results( ex, read_length, genome_size,
                                              tests, ctrlbam=controls, name=names, 
                                              shift=merge_strands,
                                              macs_args=macs_args, via=via )
        if peak_deconvolution:
            processed['deconv'] = {}
            for name in names['tests']:
                if len(names['controls'])>1:
                    macsbed = merged_many_bed([processed['macs'][(name,c)]+"_peaks.bed" 
                                          for c in names['controls']], via=via)
                elif names['controls']==[None]:
                    macsbed = processed['macs'][(name,)]+"_peaks.bed"
                else:
                    macsbed = merge_many_bed(ex,[processed['macs'][(name,x)]+"_peaks.bed" for x in names['controls']],via=via)
                                             
                deconv = run_deconv( ex, wigs[name], macsbed, chromosomes,
                                     read_length, script_path, via=via )
                [ex.add(v, description=k+':'+name+'_deconv.'+k)
                 for k,v in deconv.iteritems()]
                processed['deconv'][name] = deconv
    return (processed,gid2name)
