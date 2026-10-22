"""Preserve complete routed review/helper Git blobs without newline conversion."""
import base64,hashlib,json,subprocess
from pathlib import Path

blobs=['51a1415c5d24893077ce450d02d5826023544c2d','78906b8c34c4ef2abce0c14dedf0a89a5a7d032b','9704c2c5e5281f8c0f8b925f0599d0a2d47c6e35',
    'b116d0a472f6a9ae6a596f1744500e7fffb389b5','d492bfd0a234880be6f3becf3389bf3cb57915f2','2243b75b54bb9e3ce6a417300fc9d38c6754b7ad',
    'd2c40475cb4e8c5e9130a16cbe4cc9fc5b36c92a','a5b9c5ee8c4428ab72d2291f83a1a8c7edf1ece6','a5bf24139fcbf40f45048f45fd989d6dec0378b6','78702c2949dbb0f7c03b1e5e8fadf347b2c802d1',
    'dfb569068d33c2d08d5d41b41ea29e80c0579428','1f1eca0cc460f195612402870ce78bb4c03dd813','7538b2b914d1d55e4de36de1915a52e24f523aa3','cf75e7bee8bfc3dc21506d91e09358724eac9fe9',
    '4b52a422a7172b73faed5664e5e47668ab17c5b2','95fe61d999f43fa6e0157ff3d3314cbd10ad3b55','040fd1b139dac4ac1fcde00b4d48d8bad4d8de57',
    '33deca2a567ebf18d17222932c0513790465dcd8','e6bbbfc484db442437662e3c8ecfdcd3ea80e20d','e6c33684acce7df92612baa2f0076c4dc51a1f83',
    '0a0d527541aaa37dce6fb16da363d1d8de308df0','4cec8d09f4e3cf6408f174d8a53edc7207eefb5f','83527f55122f346384fd38dd36430e20b7226972',
    '0636e576ed4500fb9842079063f9fc60e70dcb4d','fb992718bde3b6bac894cdcae021d9e7092a0a53','82cc584e79e73beed115cdeff5d67701d21c8c69','ef0175fce010f909f816d5f5afb6f9c4b13bdc78',
    '00d2c74eb66de47582326c5e7f35ee50d893b15d','2e5fa6e11a8cb8663e39b732e19e42f604acf90c','d192c0004344f1f83eb810c8397c5105fe77e624',
    '308baee210d3ef3a6295aa3112b9a8ff606704e4','f90095eafed3d8ace03035dcb765156a719a0976','ca10b41375fcff25bdcece244db292f6870f0630','bdef2d3341f3625b19184cdf9d2d5c1511a8ddb7',
    '6ee11a692f9b53563f13282297158876f2c46950','b5a2b5f5f824558110a28b2cc6ce5f13ef73869f','9c10db204cf0d6ebe1f84b81b2b63bf6e3b22505','495ba85a7b851b37d428e72fc21d08a3e9aa88c9','0b74970f62378b5b8ed08f6d70785f97ffac2d0c',
    '918e706667978c0b9791ba788d5116dfcb6707b4','1122fffe9655a6ca4b1578cc9dcc71d60ec9da3e','25b434355f70738b0c81efab2aa85d36357019fd','66d45925d5f70fe3929e2d7fef0266c3f1d151c1',
    'c0816106b11ac9ba95789c7b0298ba40e8ce70e1','dccd4748bc3dff77e93a0d7b2cdb08bad8828a6e','51c104c262a7600a889686bef8d2cb55d92b1d33','4653a00e72cd4759016393ce507150e694761fa2',
    '680d080226f507f3975f2dfa2959cf285d0e9e14','d2efd2237b183324b002cc6a27e31abdfb29958b','91fd03edfdee6eb4aa91ec181710a72f8945b499',
    'b501f08f6913085b8cc0f8e4597b494bda284dc9','2395aae8410f4fe4c8a1a997906f06845b6bc107','fd8352c7cacb3a89715ffc48156bf67f8f4f3226','57b6e1843e097ea0a007a8f30bae613d615f9d6c']
items=[]
for blob in blobs:
    raw=subprocess.check_output(['git','cat-file','blob',blob])
    actual=subprocess.check_output(['git','hash-object','--stdin'],input=raw).decode().strip()
    assert actual==blob
    items.append(dict(git_blob=blob,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),base64=base64.b64encode(raw).decode()))
target=Path('docs/implementation/evidence/G1-LIVE-HOLD/raw-supplement-review-and-compatibility.json')
target.write_text(json.dumps(items,indent=2)+'\n',encoding='utf-8')
print(json.dumps([{k:v for k,v in item.items() if k!='base64'} for item in items]))
