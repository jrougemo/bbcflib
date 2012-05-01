"""
===========================
Module: bbcflib.demultiplex
===========================

"""
from bein import program
from bein.util import touch, add_pickle, split_file, count_lines
from common import set_file_descr, gzipfile, unique_filename_in, cat
from bbcflib import daflims
from mapseq import bowtie_build, bowtie,get_fastq_files#, add_bowtie_index
import os, urllib, shutil, re

#MLPath="/archive/epfl/bbcf/mleleu/pipeline_vMarion/pipeline_3Cseq/vWebServer_Bein/"

@program
def exportToFasta(exportFile,n=1,x=22,output=None):
    faFile=output or unique_filename_in()
    return{'arguments': ["exportToFasta.py","-i",exportFile,"-n",str(n),"-x",str(x)],
           'return_value':faFile}

@program
def fastqToFasta(fqFile,n=1,x=22,output=None):
    faFile=output or unique_filename_in()
    return{'arguments': ["fastqToFasta.py","-i",fqFile,"-o",faFile,"-n",str(n),"-x",str(x)],
           'return_value':faFile}

def split_exonerate(filename,n=1,x=22,l=30):
    correction={}
    files = {}
    filenames={}

    with open(filename,"r") as f:
        for s in f:
            if not(re.search(r'vulgar',s)): continue
            s=s.strip('\n').split(' ')
            s_split = s[5].split('|')
            key = s_split[0]
            if not key in correction:
                if len(s_split) > 3:
                    correction[key]=len(s_split[1])-len(s_split[3])+1
                else:
                    correction[key]=len(s_split[1])+1
                filenames[key]=unique_filename_in()
                files[key]=open(filenames[key],"w")
            k=int(s[3])-int(s[7])+correction[key]
            info=s[1].split('_')
            l_linename=len(info[0])
            l_seq=len(info[1])
            full_qual=s[1][int(l_linename)+int(l_seq)+2:int(l_linename)+2*int(l_seq)+2]
            seq=info[1][k:l+k]
            qual=full_qual[k:l+k]
            files[key].write("@"+info[0]+"_"+seq+"_"+qual+"\n"+seq+"\n+\n"+qual+"\n")
    for f in files.itervalues():
        f.close()
    return filenames

@program
def exonerate(fastaFile,dbFile,minScore=77,n=1,x=22,l=30):
    return{'arguments': ["exonerate","--showalignment","no","--model","affine:local",
                         "-o","-4","-e","-12","-s",str(minScore),fastaFile,dbFile],
           'return_value': None}

def parallel_exonerate(ex, subfiles, dbFile, grp_name, 
                       minScore=77, n=1, x=22, l=30, via="local"):
    futures=[fastqToFasta.nonblocking(ex,sf,n=n,x=x,via=via) for sf in subfiles]

    futures2 = []
    res = []
    resExonerate = []
    faSubFiles=[]
    for sf in futures:
        subResFile = unique_filename_in()
        faSubFiles.append(sf.wait())
        futures2.append(exonerate.nonblocking(ex,faSubFiles[-1],dbFile,minScore=minScore,n=n,x=x,l=l,via=via,stdout=subResFile,memory=6))
        resExonerate.append(subResFile)
    for n,f in enumerate(resExonerate):
        futures2[n].wait()
        resSplitExonerate=split_exonerate(f,n=n,x=x,l=l)
        res.append(resSplitExonerate)

    gzipfile(ex,faSubFiles[0])
    ex.add(faSubFiles[0]+".gz",
           description=set_file_descr(grp_name+"_input_part.fa.gz",
                                      group=grp_name,step="init",type="fa",
                                      view="admin",comment="part") )
    gzipfile(ex,resExonerate[0])
    ex.add(resExonerate[0]+".gz",
           description=set_file_descr(grp_name+"_exonerate_part.txt.gz",
                                      group=grp_name,step="exonerate",type="txt",
                                      view="admin",comment="part") )
    return res

def demultiplex(ex,subFiles,dbFile,grp_name,minScore=77,n=1,x=22,l=30,via="local"):
    exonerated = parallel_exonerate(ex, subFiles, dbFile, grp_name, minScore=int(minScore),n=n,x=x,l=int(l),via=via)
    
    resFiles = dict((k,'') for d in exonerated for k in d.keys())
    for k in resFiles.keys():
        v = [d[k] for d in exonerated if k in d]
        resFiles[k] = cat(v[1:],out=v[0])
    return resFiles

def load_paramsFile(paramsfile):
    '''
    Return a dictionary with the parameters required for exonerate
    '''
    params={}
    with open(paramsfile) as f:
        for s in f:
            if re.search('^#',s): continue
            (k,v)=s.strip().split('=')
            if re.search('Search the primer from base i',k): 
                params['n']=v
            if re.search('Search the primer in the next n bps of the reads',k):
                params['x']=v
            if re.search('Minimum score for Exonerate',k):
                params['s']=v
            if re.search('Generate fastq output files',k):
                if re.search('Y',v) or re.search('y',v):
                    params['q']=True
                else:
                    params['q']=False
            if re.search('Length of the reads to align',k):
                params['l']=v
    return params

def prepareReport(ex,name,tot_counts,counts_primers,counts_primers_filtered):
    """
    Example::
        Primer  Total_number_of_reads   nFiltered       nValidReads
        HoxD13  9406932 4296211 5110721
        HoxD4   3835395 415503  3419892
        HoxD9   6908054 594449  6313605
        Unclassified    1304048
        Total   21454429
    """
    tot_counts_primers = sum(counts_primers.values())
    dataReport = unique_filename_in()
    out = open(dataReport,'w')
    out.write("Primer\tTotal_number_of_reads\tnFiltered\tnValidReads\n")
    for k,v in counts_primers.iteritems():
        if counts_primers_filtered[k]>0:
            nFiltered=v-counts_primers_filtered[k]
        else:
            nFiltered=0
            counts_primers_filtered[k]=v
        out.write("\t".join([str(x) for x in [k,v,nFiltered,counts_primers_filtered[k]]])+"\n")
    out.write("Unclassified\t"+str(tot_counts-tot_counts_primers)+"\n")
    out.write("Total\t"+str(tot_counts)+"\n")
    out.close()
    return (tot_counts>tot_counts_primers,dataReport)

@program
def createReport(numbersFile,reportFile,script_path='./'):
    return{'arguments': ["R","--vanilla","--no-restore","--slave","-f",
                         os.path.join(script_path,"plotGraphsDemultiplexing.R"),
                         "--args",numbersFile,reportFile],
           'return_value':None}


def workflow_groups(ex, job, gl, file_path="../", via='lsf'):
    script_path=gl['script_path']
    if 'lims' in gl:
        dafl=dict((loc,daflims.DAFLIMS( username=gl['lims']['user'], password=pwd ))
                  for loc,pwd in gl['lims']['passwd'].iteritems())
    else:
        dafl=None
	
    job=get_fastq_files(ex, job, dafl)
	
    file_names = {}
    job_groups=job.groups
    resFiles={}
    for gid, group in job_groups.iteritems():
        file_names[gid] = {}

        primersFilename = 'group_' + group['name'] + "_barcode_file.fa"
        primersFile = os.path.join(file_path,primersFilename)
        ex.add(primersFile,description=set_file_descr(primersFilename,group=group['name'],step="init",type="fa"))

        paramsFilename = 'group_' + group['name'] + "_param_file.txt"
        paramsFile = os.path.join(file_path,paramsFilename)
        ex.add(paramsFile,description=set_file_descr(paramsFilename,group=group['name'],step="init",type="txt"))
        params=load_paramsFile(paramsFile)

        infiles = []
        tot_counts = 0
        allSubFiles = []
        for rid,run in group['runs'].iteritems():
            infiles.append(run)
            n=count_lines(ex,run)
            tot_counts += n/4
            if n>10000000:
                allSubFiles.extend(split_file(ex,run,n_lines=8000000))
            else:
                allSubFiles.append(run)
        resExonerate = demultiplex(ex,allSubFiles,primersFile,group['name'],
                                   params['s'],params['n'],params['x'],params['l'],
                                   via=via)
        filteredFastq={}
        counts_primers={}
        counts_primers_filtered={}
        for k,f in resExonerate.iteritems():
            ex.add(f,description=set_file_descr(group['name']+"_"+k+".fastq",
                                                group=group['name'],step="demultiplexing",type="fastq"))
            counts_primers[k]=count_lines(ex,f)/4
            counts_primers_filtered[k]=0
            file_names[gid][k]=group['name']+"_"+k
        logfile=unique_filename_in()
        log=open(logfile,"w")
        log.write("Will get sequences to filter\n");log.flush()
        seqToFilter=getSeqToFilter(ex,primersFile)

        # if seqToFilter is NOT none...
        log.write("Will filter the sequences\n")
        filteredFastq=filterSeq(ex,resExonerate,seqToFilter,group['name'],via=via)

        log.write("After filterSeq, filteredFastq=\n")
        log.write(str(filteredFastq));log.flush()

        for k,f in filteredFastq.iteritems():
            log.write("\nWill add filtered file "+f+" with descr="+group['name']+"_"+k+"_filtered.fastq\n");log.flush()
            ex.add(f,description=set_file_descr(group['name']+"_"+k+"_filtered.fastq",
                                                group=group['name'],step="filtering",
                                                type="fastq"))
            counts_primers_filtered[k]=count_lines(ex,f)/4
            file_names[gid][k]=group['name']+"_"+k+"_filtered"

        ex.add(logfile,description=set_file_descr("logfile",group=group['name'],
                                                  step="final",type="txt",view="admin"))
        # Prepare report per group of runs
        report_ok,reportFile=prepareReport(ex,group['name'],tot_counts,
                                           counts_primers,counts_primers_filtered)
        ex.add(reportFile,description=set_file_descr(
                group['name']+"_report_demultiplexing.txt",
                group=group['name'],step="final",type="txt",view="admin"))
        if report_ok:
            reportFile_pdf=unique_filename_in()
            createReport(ex,reportFile,reportFile_pdf,script_path)
            ex.add(reportFile_pdf,description=set_file_descr(
                    group['name']+"_report_demultiplexing.pdf",
                    group=group['name'],step="final",type="pdf"))
        else:
            log.write("*** Probable ambiguous classification: total_reads < sum(reads_by_primers) ***\n");log.flush()
    add_pickle( ex, file_names, 
                set_file_descr('file_names',step="final",type='py',view='admin') )
    return resFiles


def getSeqToFilter(ex,primersFile):
    allSeqToFilter={}
    filenames={}
    with open(primersFile,"r") as f:
        for s in f:
            if not(re.search(r'^>',s)): continue
            s_split=s.split('|')
            key=s_split[0].replace(">","")
            filenames[key]=unique_filename_in()
            allSeqToFilter[key]=open(filenames[key],"w")
            for i in range(4,len(s_split)):
                if not re.search('Exclude',s_split[i]):
                    allSeqToFilter[key].write(">seq"+str(i)+"\n"+s_split[i].replace(".","")+"\n")

    for f in allSeqToFilter.values(): f.close()
    return filenames


def filterSeq(ex,fastqFiles,seqToFilter,grp_name,via='lsf'):
#seqToFilter=`awk -v primer=${curPrimer} '{if($0 ~ /^>/){n=split($0,a,"|");curPrimer=a[1];gsub(">","",curPrimer); if(curPrimer == primer){seqToFilter="";for(i=5;i<n;i++){if(a[i] !~ /Exclude=/){seqToFilter=seqToFilter""a[i]","}} if(a[n] !~ /Exclude=/){seqToFilter=seqToFilter""a[n]}else{gsub(/,$/,"",seqToFilter)};print seqToFilter}}}' ${primersFile}`
    indexSeqToFilter={}
    indexFiles={}
    for k,f in seqToFilter.iteritems():
        ex.add(f,description=set_file_descr(grp_name+"_"+k+"_seqToFilter.fa",
                                            group=grp_name,step="filtering",
                                            type="fa",view="admin"))
        if k in fastqFiles:
            indexFiles[k]=bowtie_build.nonblocking(ex,f,via=via)

    unalignedFiles={}
    futures=[]
    bwtarg=["-a","-q","-n","2","-l","20","--un"]
    for k,f in indexFiles.iteritems():
        unalignedFiles[k]=unique_filename_in()
        touch(ex,unalignedFiles[k])
        futures.append(bowtie.nonblocking( ex, f.wait(), fastqFiles[k],
                                           bwtarg+[unalignedFiles[k]], via='lsf'))

    for f in futures: f.wait()
    return unalignedFiles

