"""Preserve complete routed review/helper Git blobs without newline conversion."""
import base64,hashlib,json,subprocess
from pathlib import Path

blobs=['51a1415c5d24893077ce450d02d5826023544c2d','78906b8c34c4ef2abce0c14dedf0a89a5a7d032b','9704c2c5e5281f8c0f8b925f0599d0a2d47c6e35',
    'b116d0a472f6a9ae6a596f1744500e7fffb389b5','d492bfd0a234880be6f3becf3389bf3cb57915f2','2243b75b54bb9e3ce6a417300fc9d38c6754b7ad',
    'd2c40475cb4e8c5e9130a16cbe4cc9fc5b36c92a','a5b9c5ee8c4428ab72d2291f83a1a8c7edf1ece6','a5bf24139fcbf40f45048f45fd989d6dec0378b6','78702c2949dbb0f7c03b1e5e8fadf347b2c802d1',
    'dfb569068d33c2d08d5d41b41ea29e80c0579428','1f1eca0cc460f195612402870ce78bb4c03dd813','7538b2b914d1d55e4de36de1915a52e24f523aa3','cf75e7bee8bfc3dc21506d91e09358724eac9fe9',
    '4b52a422a7172b73faed5664e5e47668ab17c5b2','95fe61d999f43fa6e0157ff3d3314cbd10ad3b55','040fd1b139dac4ac1fcde00b4d48d8bad4d8de57',
    '33deca2a567ebf18d17222932c0513790465dcd8','e6bbbfc484db442437662e3c8ecfdcd3ea80e20d','e6c33684acce7df92612baa2f0076c4dc51a1f83']
items=[]
for blob in blobs:
    raw=subprocess.check_output(['git','cat-file','blob',blob])
    actual=subprocess.check_output(['git','hash-object','--stdin'],input=raw).decode().strip()
    assert actual==blob
    items.append(dict(git_blob=blob,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),base64=base64.b64encode(raw).decode()))
target=Path('docs/implementation/evidence/G1-LIVE-HOLD/raw-supplement-review-and-compatibility.json')
target.write_text(json.dumps(items,indent=2)+'\n',encoding='utf-8')
print(json.dumps([{k:v for k,v in item.items() if k!='base64'} for item in items]))
