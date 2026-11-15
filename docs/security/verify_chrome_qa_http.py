"""Real loopback QA HTTP checks; never emit passwords, tokens or original data."""
import json
from pathlib import Path
import subprocess
import sys
import os
import argparse
from urllib.request import Request,urlopen
from urllib.error import HTTPError

sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_chrome_discovery_qa import target,preflight,require,MANIFEST,QA,IDENTITY
import psycopg


def powershell(code,stage='QA helper',**kwargs):
    result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',code],
                          text=True,capture_output=True,timeout=30,**kwargs)
    require(result.returncode==0,f'{stage} failed (exit {result.returncode}); process output suppressed')
    return result.stdout.strip()


def verify(port=8001):
    require(port in (8001,8002),'Unapproved QA port')
    url,oid=target()
    require(oid==50640,'Unexpected approved QA OID')
    preflight(url,oid)
    listener=json.loads(powershell("""$qaListeners=@(Get-NetTCPConnection -State Listen -LocalPort 8001 -ErrorAction Stop | Where-Object LocalAddress -eq '127.0.0.1'); if($qaListeners.Count -ne 1){exit 3}; $qaProcess=Get-CimInstance Win32_Process -Filter ('ProcessId = '+$qaListeners[0].OwningProcess); if($qaProcess.CommandLine -notmatch 'run_chrome_discovery_qa[.]py' -or $qaProcess.CommandLine -notmatch '--serve'){exit 4}; [pscustomobject]@{pid=$qaProcess.ProcessId;verified_launcher=$true}|ConvertTo-Json""".replace('LocalPort 8001','LocalPort '+str(port))))
    def request(path,body=None,token=None):
        headers={'Accept':'application/json'}
        if body is not None:headers['Content-Type']='application/json'
        if token:headers['Authorization']='Bearer '+token
        req=Request(f'http://127.0.0.1:{port}/api/v1'+path,
                    data=None if body is None else json.dumps(body).encode(),headers=headers)
        try:
            with urlopen(req,timeout=15) as response:
                require(response.status==200,'Unexpected QA HTTP status')
                return json.loads(response.read()),response.headers
        except HTTPError as error:
            category={401:'AUTHENTICATION',403:'AUTHORIZATION_OR_ADMISSION',422:'VALIDATION',429:'RATE_LIMIT'}.get(error.code,'API_ERROR')
            raise RuntimeError(f'{req.get_method()} /api/v1{path}: HTTP {error.code} {category}') from None
    request('/ready')
    with psycopg.connect(host=url.host,port=url.port or 5432,user=url.username,password=url.password,
            dbname=QA,connect_timeout=5,options='-c default_transaction_read_only=on -c statement_timeout=5000') as connection:
        require(tuple(connection.execute(IDENTITY).fetchone())==(QA,oid,True),'Runtime catalog identity mismatch')
        ports=[str(row[0]) for row in connection.execute("""SELECT client_port FROM pg_stat_activity
            WHERE datname=%s AND pid<>pg_backend_pid() AND client_port>0""",(QA,))]
    require(bool(ports),'QA backend database session not found')
    runtime=powershell("""$qaPorts=@($env:WHATNOT_QA_CLIENT_PORTS.Split(',')|ForEach-Object{[int]$_}); $qaConnections=@(Get-NetTCPConnection -State Established -RemotePort 5432 | Where-Object {$_.RemoteAddress -in @('127.0.0.1','::1') -and $_.LocalPort -in $qaPorts -and $_.OwningProcess -eq [int]$env:WHATNOT_QA_PROCESS_ID}); if($qaConnections.Count -lt 1){exit 5}; 'VERIFIED'""",
        stage='QA socket correlation',env={**os.environ,'WHATNOT_QA_CLIENT_PORTS':','.join(ports),'WHATNOT_QA_PROCESS_ID':str(listener['pid'])})
    require(runtime=='VERIFIED','QA worker database correlation failed')
    manifest=json.loads(MANIFEST.read_text())
    encrypted=Path(manifest['private_credentials_path']).read_text()
    plaintext=powershell("$qaSecure=ConvertTo-SecureString -String ([Console]::In.ReadToEnd()); [System.Net.NetworkCredential]::new('', $qaSecure).Password",stage='QA credential decryption',input=encrypted)
    credentials=json.loads(plaintext)
    auth,_=request('/auth/login',{'email':credentials['buyer_email'],'password':credentials['buyer_password']})
    token=auth['access_token']
    require(auth['user']['role']=='BUYER','Unexpected authenticated QA role')
    results=[]
    for point,count in [({'latitude':0,'longitude':0},2),({'latitude':1,'longitude':1},0),({'latitude':0,'longitude':0},2)]:
        products,headers=request('/discovery/products',{'location':point},token)
        require(len(products)==count and headers.get('Cache-Control')=='no-store','QA discovery count/cache mismatch')
        if count:
            require({p['name']:p['price'] for p in products}=={'QA Nearby Vase':'250.00','QA Nearby Basket':'125.50'},'QA product names/prices mismatch')
            require(all(p['shop_name']=='Chrome QA Maker' and not p['is_verified'] for p in products),'QA seller display differs')
            require(all(not {'latitude','longitude','distance_km','phone','address','seller'} & p.keys() for p in products),'Unexpected private discovery fields')
        results.append(len(products))
    addresses,_=request('/addresses',token=token)
    require(len(addresses)==1 and addresses[0]['pincode']=='999999','QA saved address differs')
    fallback,_=request('/discovery/products',{'address_id':addresses[0]['id']},token)
    require(len(fallback)==2,'QA owned-address discovery failed')
    radius_checks=[]
    for radius in (1,2,3):
        for point,expected,label in [({'latitude':0,'longitude':0},2,'origin'),
            ({'latitude':0,'longitude':.012},0 if radius==1 else 1,'between_one_and_two_km'),
            ({'latitude':1,'longitude':1},0,'unsupported')]:
            products,_=request('/discovery/products',{'location':point,'radius_km':radius},token)
            require(len(products)==expected,'Real HTTP radius filtering differs')
            if label=='between_one_and_two_km' and expected:
                require(products[0]['name']=='QA Nearby Vase','Smaller product radius bypassed')
            radius_checks.append({'radius_km':radius,'synthetic_case':label,'status':200,'count':len(products)})
    state=preflight(url,oid)
    result={'status':'PASS','api':f'http://127.0.0.1:{port}/api/v1','database':QA,'oid':oid,'revision':'0009',
        'runtime_database_identity':'VERIFIED','server_process_id':listener['pid'],
        'supported_unsupported_supported_counts':results,'owned_address_result_count':len(fallback),
        'product_prices':{'QA Nearby Vase':'250.00','QA Nearby Basket':'125.50'},
        'seller':'Chrome QA Maker','pending_product_excluded':True,'cache_no_store':True,
        'private_fields_omitted':True,'fixture_counts_after_http':state['counts'],
        'radius_http_checks':radius_checks,'credentials_or_tokens_emitted':False,'real_chrome_user_acceptance':'NOT VERIFIED'}
    (Path(__file__).parent/'evidence/chrome-qa-http.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    try:
        parser=argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--port',type=int,choices=(8001,8002),default=8001)
        verify(parser.parse_args().port)
    except Exception as error:
        print(json.dumps({'status':'STOP','exception_class':type(error).__name__,
            'message':str(error) if type(error) is RuntimeError else 'Private HTTP/connection inputs suppressed'}),flush=True)
        raise SystemExit(1)
