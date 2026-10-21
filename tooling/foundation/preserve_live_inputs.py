"""Preserve complete routed review/helper Git blobs without newline conversion."""
import base64,hashlib,json,subprocess
from pathlib import Path

blobs=['51a1415c5d24893077ce450d02d5826023544c2d','78906b8c34c4ef2abce0c14dedf0a89a5a7d032b','9704c2c5e5281f8c0f8b925f0599d0a2d47c6e35',
    'b116d0a472f6a9ae6a596f1744500e7fffb389b5','d492bfd0a234880be6f3becf3389bf3cb57915f2','2243b75b54bb9e3ce6a417300fc9d38c6754b7ad',
    'd2c40475cb4e8c5e9130a16cbe4cc9fc5b36c92a','a5b9c5ee8c4428ab72d2291f83a1a8c7edf1ece6','a5bf24139fcbf40f45048f45fd989d6dec0378b6','78702c2949dbb0f7c03b1e5e8fadf347b2c802d1']
items=[]
for blob in blobs:
    raw=subprocess.check_output(['git','cat-file','blob',blob])
    actual=subprocess.check_output(['git','hash-object','--stdin'],input=raw).decode().strip()
    assert actual==blob
    items.append(dict(git_blob=blob,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),base64=base64.b64encode(raw).decode()))
target=Path('docs/implementation/evidence/G1-LIVE-HOLD/raw-supplement-review-and-compatibility.json')
target.write_text(json.dumps(items,indent=2)+'\n',encoding='utf-8')
print(json.dumps([{k:v for k,v in item.items() if k!='base64'} for item in items]))
