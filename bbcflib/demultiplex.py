"""
===========================
Module: bbcflib.demultiplex
===========================

"""
from bein import program
from bein.util import touch, add_pickle, split_file, count_lines
from common import set_file_descr, gzipfile, unique_filename_in, cat
from bbcflib import daflims
from mapseq import bowtie_build, bowtie, get_fastq_files
import os, urllib, shutil, sys, tarfile

bcDelimiter = ':' ## '_' might be replaced by ';' or ':'


@program
def fastqToFasta(fqFile,n=1,x=22,output=None):
    if output is None: output = unique_filename_in()
    return {'arguments': ["fastqToFasta.py","-i",fqFile,"-o",output,"-n",str(n),"-x",str(x)],
            'return_value': output}

def split_exonerate(filename,primersDict,minScore,l=30,n=1,trim=True):

    correction = {}
    files = {}
    filenames = {}
    alignments = {}
    prev_idLine = ''
    # Is ambiguous a read with multiple equally good exonerate alignments (i.e. with a same score >= minScore)
    # Will often be empty as it contains only good alignments (>minScore).
    # Other ambiguous but "bad" alignments will be in "unaligned"
    alignments["ambiguous"] = unique_filename_in()
    files["ambiguous"] = open(alignments["ambiguous"],"w")
    alignments["ambiguous_fastq"] = unique_filename_in()
    files["ambiguous_fastq"] = open(alignments["ambiguous_fastq"],"w")
    # Is unaligned a read with score < minScore (that is score between my_minScore and minScore)
    # my_minScore is the score used for exonerate and is ~ equal to half the length of the primer sequence
    alignments["unaligned"] = unique_filename_in()
    files["unaligned"] = open(alignments["unaligned"],"w")
    # discarded: if score ok but len(seq) < l (that is the remaining sequence is too short)
    alignments["discarded"] = unique_filename_in()
    files["discarded"] = open(alignments["discarded"],"w")
    line_buffer = []

    def _process_line(line_buffer):
        if len(line_buffer) == 1:
            files[line_buffer[0][3]].write(line_buffer[0][1])
        elif len(line_buffer)>1:
            for buf in sorted(line_buffer):
                files["ambiguous"].write(" ".join(buf[2])+"\n")
            # add the corresponding ambiguous read to the ambiguous_fastq file (only once)
            #files["ambiguous_fastq"].write(" ".join(buf[1])+"\n")
            files["ambiguous_fastq"].write(buf[1])

    with open(filename,"r") as f:
        for s in f:
            if not s[:7] == 'vulgar:': continue
            s = s.strip().split(' ')
            s_split = s[5].split('|')
            key = s_split[0]
            info = s[1].split('_')
            idLine = info[0]
            if idLine != prev_idLine:
                _process_line(line_buffer)
                line_buffer = []
            prev_idLine = idLine

            closestBarcode = key
            global bcDelimiter
            if key.split(bcDelimiter)[0] in primersDict: ## has barcode
                pr = key.split(bcDelimiter)[0]
                closestBarcode = getClosestBarcode(info[1],primersDict[pr]) ## replace key with the closest barcode

            if key not in correction:
                if len(s_split) > 3:
                    correction[key] = len(s_split[1])-len(s_split[3])+n-1
                else:
                    correction[key] = len(s_split[1])+n-1

                if len(key.split(bcDelimiter)) > 1:
                    correction[key] = correction[key] - 1 ## remove the bcDelimiter from the correction

                filenames[key] = unique_filename_in()
                files[key] = open(filenames[key],"w")
            k = int(s[3])-int(s[7])+correction[key]
            if len(key.split(bcDelimiter)) > 1:
                k = k - len(primersDict[key.split(bcDelimiter)[0]][key])

            l_linename = len(info[0])
            l_seq = len(info[1])
            full_qual = s[1][int(l_linename)+int(l_seq)+2:int(l_linename)+2*int(l_seq)+2]
            if trim:
                seq = info[1][k:l+k] if l+k < l_seq else info[1][k:]; ## if not take the remaining length
                qual = full_qual[k:l+k] if l+k < l_seq else full_qual[k:]
            else:
                seq = info[1]
                qual = full_qual
            if int(s[9]) < minScore:
                files["unaligned"].write(" ".join(s)+"\n")
            elif len(seq) >= l/2:
                if key == closestBarcode or closestBarcode == "amb": # if not => not the primer_barcode to which the read comes from + add if ambiguous barcode
                    #line_buffer.append((s[9],"@"+info[0]+"\n"+seq+"***"+info[1]+"\n+\n"+qual+"\n",s,key))
                    line_buffer.append((s[9],"@"+info[0]+"\n"+seq+"\n+\n"+qual+"\n",s,key))
            else: ## will be discarded if remaining read length is too short. Arbitrarly set to < l/2. It used to be < l but will not happen as we now accept l close to the read length.
                files["discarded"].write("@"+info[0]+"\n"+seq+"\n+\n"+qual+"\n")

    _process_line(line_buffer)
    for f in files.itervalues():
        f.close()
    return (filenames,alignments)

@program
def exonerate(fastaFile,dbFile,minScore=77):
    return{'arguments': ["exonerate","--showalignment","no","--model","affine:local",
                         "-o","-4","-e","-12","-s",str(minScore),fastaFile,dbFile],
           'return_value': None}

def _get_minscore(dbf):
    with open(dbf) as df:
        firstl = df.readline()
        firstl = df.readline()
        primer_len = len(firstl)-1
## max score = len*5, penalty for len/2 mismatches = -9*len/2 => score = len/2
    return primer_len/2


def get_primersList(primersfile):
    '''
    Return a dictionary with all primers with at least one barcode occurrence
    '''
    primers = {}
    global bcDelimiter
    with open(primersfile) as f:
        for s in f:
            if s[0] == '>':
                s = s.replace('>','')
                s_split = s.strip().split('|')
                key = s_split[0]
                key_split = key.split(bcDelimiter)
                pr = key_split[0]
                if len(key_split) > 1: ## add only barcoded primers
                    bcSeq = s_split[1].split(bcDelimiter)[0]
                    if pr not in primers:
                        primers[pr] = {}
                    primers[pr][key] = bcSeq

    with open(primersfile) as f:
        for s in f:
            if s[0] == '>':
                s = s.replace('>','')
                s_split = s.strip().split('|')
                key = s_split[0]
                key_split = key.split(bcDelimiter) ## '_' might be replaced by ';' or ':'
                pr = key_split[0] if len(key_split) > 1 else key
                if len(key_split) < 2 and pr in primers: ## not barcoded but other occurrences of the same primer are.
                    bcExistSeq = primers[pr].itervalues().next()
                    bcSeq = s_split[1][:len(bcExistSeq)]
                    primers[pr][key]=bcSeq

    return primers

def countident(seq1,seq2):
    """Count the common letters in both sequencies
    """
    count = 0
    for i in range(min(len(seq1),len(seq2))):
        if seq1[i]==seq2[i]: count += 1

    return(count)

def getClosestBarcode(seq, bcList):
    max = 0
    closestBc = ''
    for bc,bcSeq in bcList.items():
        curIdent=countident(seq, bcSeq)
        if curIdent > 1: ## define a minimum identity value to avoid "wrong" sequences (identity score too low) to be associated to one barcode
            if curIdent == max : ## ambiguous
                closestBc = "amb"
            if curIdent > max :
                closestBc = bc
                max = curIdent

    return closestBc


def parallel_exonerate(ex, subfiles, dbFile, grp_descr,
                       minScore=77, n=1, x=22, l=30, trim=True, via="local"):
    futures = [fastqToFasta.nonblocking(ex,sf,n=n,x=x,via=via) for sf in subfiles]

    futures2 = []
    res = []
    resExonerate = []
    faSubFiles = []
    all_ambiguous = []
    all_ambiguous_fastq = []
    all_unaligned = []
    all_discarded = []
    gid, grp_name = grp_descr
    my_minscore = _get_minscore(dbFile)
    primersDict = get_primersList(dbFile)

    for sf in futures:
        subResFile = unique_filename_in()
        faSubFiles.append(sf.wait())
        futures2.append(exonerate.nonblocking(ex, faSubFiles[-1], dbFile, minScore=my_minscore,
                                              via=via, stdout=subResFile, memory=6))
        resExonerate.append(subResFile)
    for nf,f in enumerate(resExonerate):
        futures2[nf].wait()
        (resSplitExonerate,alignments) = split_exonerate(f, primersDict, minScore, l=l, n=n, trim=trim)
        all_unaligned.append(alignments["unaligned"])
        all_ambiguous.append(alignments["ambiguous"])
        all_ambiguous_fastq.append(alignments["ambiguous_fastq"])
        all_discarded.append(alignments["discarded"])
        res.append(resSplitExonerate)


    # add unaligned file only if it is not empty
    n = count_lines(ex,all_unaligned[0])
    if n > 1:
        catfile = cat(all_unaligned)
        gzipfile(ex,catfile)
        ex.add(catfile+".gz",
           description=set_file_descr(grp_name+"_unaligned.txt.gz",
                                      groupId=gid,step="exonerate",type="txt",
                                      view="admin", comment="scores between %i and %i"%(my_minscore,minScore)) )

    # add ambiguous file only if it is not empty
    n = count_lines(ex,all_ambiguous[0])
    if n > 1:
        catfile = cat(all_ambiguous)
        gzipfile(ex,catfile)
        ex.add(catfile+".gz",
               description=set_file_descr(grp_name+"_ambiguous.txt.gz",
                                      groupId=gid,step="exonerate",type="txt",
                                      view="admin", comment="multiple equally good classifications") )

    # add ambiguous fastq file only if it is not empty
    tot_ambiguous = count_lines(ex,all_ambiguous_fastq[0])/4
    if tot_ambiguous > 1:
        catfile = cat(all_ambiguous_fastq)
        gzipfile(ex,catfile)
        ex.add(catfile+".gz",
               description=set_file_descr(grp_name+"_ambiguous.fastq.gz",
                                      groupId=gid,step="exonerate",type="fastq", comment="multiple equally good classifications") )

    # add discarded file only if it is not empty
    tot_discarded = count_lines(ex,all_discarded[0])/4
    if tot_discarded > 1:
        catfile = cat(all_discarded)
        gzipfile(ex,catfile)
        ex.add(catfile+".gz",
               description=set_file_descr(grp_name+"_discarded.fastq.gz",
                                          groupId=gid, step="exonerate", type="fastq",
                                          view="admin", comment="remaining seq too short") )

    ## add part input fasta file only if it is not empty
    n = count_lines(ex,faSubFiles[0])
    if n > 1:
        gzipfile(ex,faSubFiles[0])
        ex.add(faSubFiles[0]+".gz",
           description=set_file_descr(grp_name+"_input_part.fa.gz",
                                      groupId=gid, step="init", type="fa",
                                      view="admin", comment="part") )


    ## add part res exonerate only if it is not empty
    n = count_lines(ex,resExonerate[0])
    if n > 1:
        gzipfile(ex,resExonerate[0])
        ex.add(resExonerate[0]+".gz",
           description=set_file_descr(grp_name+"_exonerate_part.txt.gz",
                                      groupId=gid, step="exonerate", type="txt",
                                      view="admin", comment="part") )

    resFiles = dict((k,'') for d in res for k in d.keys())
    for k in resFiles.keys():
        v = [d[k] for d in res if k in d]
        resFiles[k] = cat(v[1:],out=v[0])

    return (resFiles, tot_ambiguous, tot_discarded)

def load_paramsFile(paramsfile):
    '''
    Return a dictionary with the parameters required for exonerate
    '''
    params = {}
    with open(paramsfile) as f:
        for s in f:
            if s[0] == '#' or '=' not in s: continue
            (k,v) = s.strip().split('=')
            if 'Search the primer from base i' in k: params['n'] = int(v)
            if 'Search the primer in the next n bps of the reads' in k: params['x'] = int(v)
            if 'Minimum score for Exonerate' in k:   params['minScore'] = int(v)
            if 'Generate fastq output files' in k:   params['q'] = ('Y' in v.upper())
            if 'Length of the reads to align' in k:  params['l'] = int(v)
            if 'Trim read' in k:
                params['trim'] = ('Y' in v.upper()) or ('T' in v.upper())
            else:
                params['trim'] = True
    return params

def prepareReport(ex, name, tot_counts, counts_primers, counts_primers_filtered,
                  tot_ambiguous=0, tot_discarded=0):
    """
    Example::
        Primer  Total_number_of_reads   nFiltered       nValidReads
        HoxD13  9406932 4296211 5110721
        HoxD4   3835395 415503  3419892
        HoxD9   6908054 594449  6313605
        Discarded   xxxx
        Ambiguous   xxx
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
    out.write("Discarded\t"+str(tot_discarded)+"\n")
    out.write("Ambiguous\t"+str(tot_ambiguous)+"\n")
    tot=tot_counts_primers+tot_discarded+tot_ambiguous
    out.write("Unclassified\t"+str(tot_counts-tot)+"\n")
    out.write("Total\t"+str(tot_counts)+"\n")
    out.close()
    return (tot_counts>tot_counts_primers,dataReport)

@program
def createReport(numbersFile,reportFile,script_path='./'):
    return{'arguments': ["R","--vanilla","--no-restore","--slave","-f",
                         os.path.join(script_path,"plotGraphsDemultiplexing.R"),
                         "--args",numbersFile,reportFile],
           'return_value':None}


def demultiplex_workflow(ex, job, gl, file_path="../", via='lsf',
                         logfile=sys.stdout, debugfile=sys.stderr):
    script_path = gl['script_path']
    file_names = {}
    job_groups=job.groups
    resFiles={}
    for gid, group in job_groups.iteritems():
        file_names[gid] = {}

        primersFilename = 'group_' + group['name'] + "_barcode_file.fa"
        primersFile = group.get("primersfile",os.path.join(file_path,primersFilename))
        ex.add(primersFile,description=set_file_descr(primersFilename,groupId=gid,step="init",type="fa"))

        paramsFilename = 'group_' + group['name'] + "_param_file.txt"
        paramsFile = group.get("paramsfile",os.path.join(file_path,paramsFilename))
        ex.add(paramsFile,description=set_file_descr(paramsFilename,groupId=gid,step="init",type="txt"))
        params = load_paramsFile(paramsFile)

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
        (resExonerate, tot_ambiguous, tot_discarded) = parallel_exonerate( ex, allSubFiles, primersFile,
                                                                           (gid, group['name']), via=via, **params )

        gzipfile(ex, cat(infiles))
        ex.add(run+".gz",description=set_file_descr(group['name']+"_full_fastq.gz",
                                                    groupId=gid,step='exonerate',view='debug',type="fastq"))
        logfile.write("Will get sequences to filter\n");logfile.flush()
        seqToFilter = getSeqToFilter(ex,primersFile)

        logfile.write("Will filter the sequences\n")
        filteredFastq = filterSeq(ex,resExonerate,seqToFilter,gid,group['name'],via=via)

        logfile.write("After filterSeq, filteredFastq=%s\n" %filteredFastq);logfile.flush()

        counts_primers = {}
        counts_primers_filtered = {}
        global bcDelimiter
        if len(filteredFastq):
            archive = unique_filename_in()
            tgz = tarfile.open(archive, "w:gz")
        for k,f in resExonerate.iteritems():
            counts_primers[k] = count_lines(ex,f)/4
            if k in filteredFastq:
                k2 = k.replace(bcDelimiter,"_")
                file_names[gid][k2] = group['name']+"_"+k2+"_filtered"
                ex.add(filteredFastq[k],description=set_file_descr(file_names[gid][k2]+".fastq",
                                                                   groupId=gid,step="final",
                                                                   type="fastq"))
                counts_primers_filtered[k] = count_lines(ex,filteredFastq[k])/4
                tgz.add( f, arcname=group['name']+"_"+k.replace(bcDelimiter,"_")+".fastq" )
            else:
                k2 = k.replace(bcDelimiter,"_")
                file_names[gid][k2] = group['name']+"_"+k2
                ex.add(f,description=set_file_descr(file_names[gid][k2]+".fastq",
                                                    groupId=gid,step="final",
                                                    type="fastq"))
                counts_primers_filtered[k] = 0
        if len(filteredFastq):
            tgz.close()
            ex.add(archive,description=set_file_descr(group['name']+"_unfiltered_fastq.tgz",
                                                      groupId=gid,step="exonerate",
                                                      type="tar"))

        # Prepare report per group of runs
        report_ok,reportFile = prepareReport(ex,group['name'],
                                             tot_counts, counts_primers,counts_primers_filtered,
                                             tot_ambiguous, tot_discarded)
        ex.add(reportFile,description = set_file_descr(
                group['name']+"_report_demultiplexing.txt",
                groupId=gid,step="final",type="txt",view="admin"))
        if report_ok:
            reportFile_pdf = unique_filename_in()
            createReport(ex,reportFile,reportFile_pdf,script_path)
            ex.add(reportFile_pdf,description=set_file_descr(
                    group['name']+"_report_demultiplexing.pdf",
                    groupId=gid,step="final",type="pdf"))
        else:
            logfile.write("*** Probable ambiguous classification: total_reads < sum(reads_by_primers) ***\n");logfile.flush()
    add_pickle( ex, file_names,
                set_file_descr('file_names',step="final",type='py',view='admin') )
    return resFiles


def getSeqToFilter(ex,primersFile):
    filenames = {}
    with open(primersFile,"r") as f:
        for s in f:
            if s[0] != '>': continue
            s_split = s.split('|')
            key = s_split[0].replace(">","")
            filenames[key] = unique_filename_in()
            with open(filenames[key],"w") as fout:
                for i in range(4,len(s_split)):
                    if 'Exclude' not in s_split[i]:
                        fout.write(">seq"+str(i)+"\n"+s_split[i].replace(".","")+"\n")
    return filenames


def filterSeq(ex,fastqFiles,seqToFilter,gid,grp_name,via='lsf'):
    indexSeqToFilter = {}
    indexFiles = {}
    global bcDelimiter
    for k,f in seqToFilter.iteritems():
        if os.path.getsize(f) == 0: continue
        ex.add(f,description=set_file_descr(grp_name+"_"+k.replace(bcDelimiter,"_")+"_seqToFilter.fa",
                                            groupId=gid,step="filtering",
                                            type="fa",view="admin"))
        if k in fastqFiles:
            indexFiles[k] = bowtie_build.nonblocking(ex,f,via=via)

    unalignedFiles = {}
    futures = []
    bwtarg = ["-a","-q","-n","2","-l","20","--un"]
    for k,f in indexFiles.iteritems():
        unalignedFiles[k] = unique_filename_in()
        touch(ex,unalignedFiles[k])
        futures.append(bowtie.nonblocking( ex, f.wait(), fastqFiles[k],
                                           bwtarg+[unalignedFiles[k]], via='lsf'))

    for f in futures: f.wait()
    return unalignedFiles



if __name__ == "__main__":
    primersDict=get_primersList(sys.argv[2])
    (resSplitExonerate,alignments)=split_exonerate(sys.argv[1],primersDict,minScore=8,l=30,n=1,trim='False')
    res = []
    res.append(resSplitExonerate)
    resFiles = dict((k,'') for d in res for k in d.keys())
    for k in resFiles.keys():
        v = [d[k] for d in res if k in d]
        resFiles[k] = cat(v[1:],out=v[0])
    print resFiles
    print resSplitExonerate
    print alignments
    print "Done"
