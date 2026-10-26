"""Finite, sequential public discovery queue; never publishes unreviewed hits.

Can hand off from an already running Jeonnam scan without duplicate requests.
Any failed/stale job stops the queue. Checkpoints survive local interruption.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from onnuri_live import KST
from refresh_regions import ORDER

ROOT=Path(__file__).resolve().parents[1]


def jobs(directory, stamp, first_output, gap_targets=None):
    result=[]
    for area in ORDER:
        output=first_output if area=='전남' else directory/f'kb_unfiltered_{area}_{stamp}.json'
        result.append({'region':area,'output':str(output),'kind':'fuel_index'})
        if area=='전남' and gap_targets:
            result.append({'region':area,'output':str(directory/f'kb_registry_gap_{stamp}.json'),
                           'kind':'municipal_address_gap','targets':str(gap_targets)})
    return result


def wait_existing(path, stale_seconds=900):
    while True:
        data=json.loads(path.read_text(encoding='utf-8'))
        if data['status']=='candidate_queue_complete':return data
        if data['status']!='running':raise RuntimeError('Existing scan stopped: '+str(data.get('error')))
        checked=datetime.fromisoformat(data['checked_at'])
        if (datetime.now(KST)-checked).total_seconds()>stale_seconds:
            raise RuntimeError('Existing scan has no recent checkpoint; resume manually')
        time.sleep(15)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--directory',type=Path,default=ROOT/'output/alternatives')
    parser.add_argument('--stamp',default=datetime.now(KST).strftime('%Y%m%d'))
    parser.add_argument('--wait-current',type=Path)
    parser.add_argument('--gap-targets',type=Path)
    args=parser.parse_args()
    directory=args.directory.resolve();directory.mkdir(parents=True,exist_ok=True)
    status_path=directory/f'kb_region_queue_{args.stamp}.json'
    lock_path=directory/'kb_region_queue.lock'
    # O_EXCL prevents overlapping coordinators. Interrupted locks require review.
    lock=os.open(lock_path,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    os.write(lock,str(os.getpid()).encode());os.close(lock)
    first=args.wait_current.resolve() if args.wait_current else directory/f'kb_unfiltered_전남_{args.stamp}.json'
    state={'pid':os.getpid(),'status':'running','order':ORDER,'jobs':[],
           'publication':'discovery_only_requires_identity_review','error':None}
    def save():
        state['updated_at']=datetime.now(KST).isoformat(timespec='seconds')
        temp=status_path.with_suffix('.tmp');temp.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(status_path)
    try:
        for index,job in enumerate(jobs(directory,args.stamp,first,args.gap_targets)):
            state['current']=job;save()
            path=Path(job['output'])
            if index==0 and args.wait_current:
                data=wait_existing(path)
            else:
                command=[sys.executable,'-X','utf8',str(ROOT/'scripts/discover_kb_fuel.py'),
                         '--region',job['region'],'--unfiltered','--interval','3','--output',str(path)]
                if job.get('targets'):command+=['--targets',job['targets']]
                subprocess.run(command,cwd=ROOT,check=True)
                data=json.loads(path.read_text(encoding='utf-8'))
            if data['status']!='candidate_queue_complete':raise RuntimeError('Incomplete regional job')
            state['jobs'].append({**job,'completed_queries':data['completed_queries'],
                                  'planned_queries':data['planned_queries'],'status':data['status']})
            save()
        state['status']='discovery_complete_needs_review';save()
    except Exception as exc:
        state['status']='stopped_error';state['error']=str(exc);save();raise
    finally:
        lock_path.unlink(missing_ok=True)


if __name__=='__main__':main()
