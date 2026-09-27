"""Generate the minimal 1.1 structural extension; preserve the PRD schema byte-for-byte."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
schema = json.loads((root / 'contracts/prd.schema.json').read_text())
schema['$id'] = 'https://codecanopy.local/contracts/structure-1.1.schema.json'
schema['title'] = 'GREPO structure slice 1.1'
schema['$comment'] = 'Versioned extension of the supplied PRD. See contracts/README.md.'
d = schema['$defs']
d['Entity']['properties']['kind']['enum'] += ['repository', 'virtual_group']
d['Entity']['properties']['path'] = {'type': ['string', 'null']}
d['Entity']['properties'].update({'file_id': {'type': ['string','null']}, 'parent_id': {'type': ['string','null']}, 'child_count': {'type':'integer','minimum':0}, 'metadata': {'type':'object'}})
d['Relation']['properties']['kind']['enum'] += ['groups']
d['Relation']['properties']['unresolved'] = {'type': 'boolean'}
d['Coverage']['properties'].update({'total_entities': {'type':'integer','minimum':0}, 'returned_entities': {'type':'integer','minimum':0}})
d['Graph']['properties']['schema_version']['const'] = '1.1'
d['Graph']['properties'].update({'focus_path': {'type':'string'}, 'cursor':{'type':'integer','minimum':0}, 'next_cursor':{'type':['integer','null']}, 'child_total':{'type':'integer','minimum':0}})
d['AnalysisRun']['properties']['schema_version']['const'] = '1.1'
d['AnalysisRun']['properties']['stage'] = {'type':['string','null']}
d['AnalysisRun']['properties']['diagnostics'] = {'type':'array','items':{'type':'object','properties':{'file_path':{'type':['string','null']},'stage':{'type':'string'},'message':{'type':'string'},'severity':{'enum':['warning','error']}},'required':['stage','message','severity'],'additionalProperties':False}}
d['AnalysisRun']['properties'].update({'project_id':{'type':'string'},'stage_progress':{'type':['number','null'],'minimum':0,'maximum':1},'started_at':{'type':'string'},'completed_at':{'type':['string','null']},'result_snapshot_id':{'type':['string','null']}})
schema['oneOf'] = [{'$ref':'#/$defs/Graph'},{'$ref':'#/$defs/AnalysisRun'},{'$ref':'#/$defs/ApiError'}]
(root / 'contracts/structure-1.1.schema.json').write_text(json.dumps(schema,indent=2) + '\n')
