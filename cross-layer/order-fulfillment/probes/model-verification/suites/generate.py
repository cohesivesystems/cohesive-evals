"""Bounded deterministic case generation. Model inspection proposes inputs, never answers."""
import hashlib
import itertools
import json

MIN,MAX=-2147483648,2147483647
# Public task envelope, common to both conditions. Not a model-derived truth table.
STOCK=(0,1,4,7,MAX)
LIMIT=(1,4,7,MAX)

class Unsupported(ValueError):pass

def target(expr):
    kind=expr.get('$expr')
    if kind=='parameter' and expr.get('parameter')=='Quantity':return ('quantity',None)
    if kind=='constant' and type(expr.get('value')) is int:return ('constant',expr['value'])
    if kind=='field':
        segments=expr.get('path',{}).get('segments',[])
        if len(segments)==1 and segments[0].get('kind')=='Field' and segments[0].get('segment') in ('available','maxPerOrder','quarantined'):
            return ('field',segments[0]['segment'])
    raise Unsupported('Unsupported boundary operand: '+json.dumps(expr,sort_keys=True))

def boundaries(document):
    found=[];coverage=[]
    for rule in document['definition']['preconditions']:
        expr=rule['predicate'];kind=expr.get('$expr')
        if kind=='unary' and expr.get('operator')=='Not' and target(expr['operand'])==('field','quarantined'):
            coverage.append({'node':rule['id'],'kind':'boolean-toggle'});continue
        if kind!='binary' or expr.get('operator') not in ('Gt','Ge','Lt','Le','Eq','Ne'):
            raise Unsupported('Unsupported predicate at '+rule['id'])
        a,b=target(expr['left']),target(expr['right'])
        if a[0]!='quantity':a,b=b,a
        if a[0]!='quantity' or b[0] not in ('constant','field') or b==('field','quarantined'):
            raise Unsupported('No quantity threshold at '+rule['id'])
        found.append(b);coverage.append({'node':rule['id'],'kind':'threshold-neighbors','operator':expr['operator'],'threshold':b})
    return found,coverage

def generate(condition,version,document=None):
    if condition not in ('conventional','cohesive') or version not in ('original','revised'):raise ValueError('Unknown profile')
    if condition=='cohesive':thresholds,coverage=boundaries(document)
    else:
        # Ordinary hand-authored boundary/property generator; shares production rules at execution.
        thresholds=[('constant',0),('field','available'),('field','maxPerOrder')]
        coverage=[{'kind':'policy-authored-thresholds','fields':['quantity','available','maxPerOrder','quarantined']}]
    cases=[]
    for available,limit,quarantined in itertools.product(STOCK,LIMIT,(False,True)):
        state={'available':available,'maxPerOrder':limit}
        quantities={MIN,MAX,0,1,-1}
        for kind,value in thresholds:
            boundary=value if kind=='constant' else state[value]
            quantities.update(q for q in (boundary-1,boundary,boundary+1) if MIN<=q<=MAX)
        for q in sorted(quantities):
            cases.append(dict(Name='case-'+str(len(cases)),Sku='stock-😀',Available=available,
                              MaxPerOrder=limit,Quarantined=quarantined,Quantity=q))
    return {'condition':condition,'policy':version,'cases':cases,'generationCoverage':coverage,
        'modelReference':{k:document['metadata'][k] for k in ('definitionId','revisionId','fingerprint')} if document else None,
        'scope':'bounded cases; not exhaustive Int32 verification'}
