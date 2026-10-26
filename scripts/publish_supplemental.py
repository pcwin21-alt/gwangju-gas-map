"""Publish reviewed bank evidence locally without fetching or redating main data."""
from datetime import datetime
from refresh_merchants import load,save,sync_map,KST
from supplemental_onnuri import apply_evidence,reconcile_ledger


def main():
    stations,review,meta=apply_evidence(load('gas_stations.json',[]),load('merchant_review.json',[]),
        load('supplemental_onnuri_evidence.json',{}).get('rows',[]),datetime.now(KST).isoformat())
    status=load('merchant_status.json',{})
    status['supplemental_onnuri']=meta
    status['onnuri']['pending_count']=len({r['candidate_id'] for r in review if r.get('show_pending') and r.get('candidate_id')})
    ledger=load('nationwide_candidates.json',{})
    ledger['rows']=reconcile_ledger(ledger.get('rows',[]),stations)
    save('gas_stations.json',stations);save('merchant_review.json',review)
    save('merchant_status.json',status);save('nationwide_candidates.json',ledger)
    sync_map(stations,status)
    print('Stations:',len(stations),'Supplemental:',meta['confirmed_count'],'Pending:',status['onnuri']['pending_count'])


if __name__=='__main__':main()
