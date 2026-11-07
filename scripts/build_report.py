"""Generate a portable Power BI Desktop project from aggregate CSV files."""
import argparse
import base64
import csv
import json
import uuid
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FABRIC = 'https://developer.microsoft.com/json-schemas/fabric/item'
MODEL = 'RoverMOT'
SCHEMAS = {
    'Cohorts': ('cohorts', 'cohort_id:i month:s family:s age_band:s mileage_band:s tests:i initial_fails:i prs:i'),
    'Defects': ('categories', 'cohort_id:i category:s affected:i items:i'),
    'Reasons': ('reasons', 'cohort_id:i category:s rfr_id:i description:s affected:i items:i'),
    'Comparison': ('comparison', 'period:s family:s tests:i observed_rate:d adjusted_rate:d support_share:d common_strata:i'),
}
MEASURES = {
'Cohorts': {'Initial tests': ('SUM(Cohorts[tests])','#,0'),
            'Initially failed':('SUM(Cohorts[initial_fails])','#,0'),
            'Initial failure rate':('DIVIDE([Initially failed],[Initial tests])','0.0%'),
            'Passed after rectification':('SUM(Cohorts[prs])','#,0')},
'Defects': {'Affected per 1,000':("IF(HASONEVALUE('Category'[Name]),1000*DIVIDE(SUM(Defects[affected]),[Initial tests]))",'0.0'),
            'Scenario inspections':('SELECTEDVALUE(Volume[Inspections],200)','#,0'),
            'Expected affected inspections':('DIVIDE([Affected per 1,000],1000)*[Scenario inspections]','0.0')},
'Reasons': {'Recorded failure items':('SUM(Reasons[items])','#,0')},
'Comparison': {k:(f'VAR p = SELECTEDVALUE(Comparison[period],"Combined") RETURN IF(HASONEVALUE(Comparison[family]), CALCULATE(MAX(Comparison[{field}]), Comparison[period]=p))',fmt) for k,field,fmt in [
             ('Observed rate','observed_rate','0.0%'),('Standardised rate','adjusted_rate','0.0%'),
             ('Share on common support','support_share','0.0%'),('Eligible common strata','common_strata','0')]},
}
MEASURES['Comparison']['Selected comparison rate']=('IF(SELECTEDVALUE(Basis[Method],"Observed")="Observed",[Observed rate],[Standardised rate])','0.0%')


def uid(s):
    return str(uuid.uuid5(uuid.NAMESPACE_URL,'rover-mot/'+s))


def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def table(name,columns,source):
    types={'s':'string','i':'int64','d':'double'}
    return {'name':name,'lineageTag':uid(name),
            'columns':[{'name':col,'dataType':types[k],'sourceColumn':col,'summarizeBy':'none','lineageTag':uid(name+col)} for col,k in columns],
            'partitions':[{'name':name,'mode':'import','source':{'type':'m','expression':source}}],
            'measures':[{'name':k,'expression':v,'formatString':fmt,'lineageTag':uid(name+k)} for k,(v,fmt) in MEASURES.get(name,{}).items()]}


def model(data):
    tables=[]
    for name,(filename,schema) in SCHEMAS.items():
        cols=[s.split(':') for s in schema.split()]
        payload=(data/(filename+'.csv')).read_bytes()
        # Raw DEFLATE and short M literals make the project portable; no machine paths.
        compressor=zlib.compressobj(6,wbits=-15)
        encoded=base64.b64encode(compressor.compress(payload)+compressor.flush()).decode()
        parts=','.join('"'+encoded[i:i+16000]+'"' for i in range(0,len(encoded),16000))
        mtypes={'i':'Int64.Type','s':'type text','d':'type number'}
        transforms=', '.join('{"%s", %s}'%(c,mtypes[t]) for c,t in cols)
        source=['let','    Bytes = Binary.Decompress(Binary.FromText(Text.Combine({'+parts+'}),BinaryEncoding.Base64),Compression.Deflate),',
                '    Raw = Table.PromoteHeaders(Csv.Document(Bytes,[Delimiter=",",Encoding=65001,QuoteStyle=QuoteStyle.Csv])),',
                '    Typed = Table.TransformColumnTypes(Raw,{'+transforms+'},"en-GB")','in Typed']
        tables.append(table(name,cols,source))
    tables.append(table('Category',[('Name','s')],['Table.RenameColumns(Table.Distinct(Table.SelectColumns(Defects,{"category"})),{{"category","Name"}})']))
    tables.append(table('Volume',[('Inspections','i')],['Table.FromColumns({{50,100,150,200,250,300,400,500,750,1000}},type table [Inspections=Int64.Type])']))
    tables.append(table('Basis',[('Method','s')],['#table(type table [Method=text],{{"Observed"},{"Age and mileage adjusted"}})']))
    return {'name':MODEL,'compatibilityLevel':1601,'model':{'culture':'en-GB','defaultPowerBIDataSourceVersion':'powerBI_V3','sourceQueryCulture':'en-GB',
           'tables':tables,'relationships':[{'name':uid(t+'rel'),'fromTable':t,'fromColumn':'cohort_id','toTable':'Cohorts','toColumn':'cohort_id','crossFilteringBehavior':'oneDirection'} for t in ['Defects','Reasons']] + [{'name':uid(t+'category'),'fromTable':t,'fromColumn':'category','toTable':'Category','toColumn':'Name','crossFilteringBehavior':'oneDirection'} for t in ['Defects','Reasons']] }}


def field(full):
    t,c=full.split('.',1)
    kind='Measure' if c in MEASURES.get(t,{}) else 'Column'
    return {'field':{kind:{'Expression':{'SourceRef':{'Entity':t}},'Property':c}},'queryRef':full,'nativeQueryRef':c}


def report(output,data):
    parent=output; report_dir=parent/(MODEL+'.Report'); semantic=parent/(MODEL+'.SemanticModel')
    write(parent/(MODEL+'.pbip'),{'$schema':FABRIC.replace('/item','/pbip')+'/pbipProperties/1.0.0/schema.json','version':'1.0','artifacts':[{'report':{'path':report_dir.name}}],'settings':{'enableAutoRecovery':True}})
    write(semantic/'definition.pbism',{'version':'1.0','settings':{}})
    write(semantic/'model.bim',model(data))
    write(report_dir/'definition.pbir',{'version':'4.0','datasetReference':{'byPath':{'path':'../'+semantic.name}}})
    root=report_dir/'definition'
    write(root/'version.json',{'$schema':FABRIC+'/report/definition/versionMetadata/1.0.0/schema.json','version':'2.0.0'})
    write(root/'report.json',{'$schema':FABRIC+'/report/definition/report/2.1.0/schema.json','themeCollection':{}})
    pages=[]
    def page(name):
        key=uid(name).replace('-','')[:20]; pages.append(key)
        write(root/'pages'/key/'page.json',{'$schema':FABRIC+'/report/definition/page/2.0.0/schema.json','name':key,'displayName':name,'displayOption':'FitToPage','width':1280,'height':720})
        return key
    def visual(page_id,title,typ,roles,x,y,w,h):
        key=uid(page_id+title).replace('-','')[:20]
        literal=lambda v:{'expr':{'Literal':{'Value':v}}}
        conf={'visualType':typ,'query':{'queryState':{role:{'projections':[field(f) for f in fs]} for role,fs in roles.items()}},
              'visualContainerObjects':{'title':[{'properties':{'show':literal('true'),'text':literal("'"+title.replace("'","''")+"'")}}]}}
        write(root/'pages'/page_id/'visuals'/key/'visual.json',{'$schema':FABRIC+'/report/definition/visualContainer/2.1.0/schema.json','name':key,'position':{'x':x,'y':y,'z':y+x,'width':w,'height':h},'visual':conf})
    def slicer(pg,title,f,x,w=270):
        visual(pg,title,'slicer',{'Values':[f]},x,8,w,117)
    def chart(pg,title,typ,cat,val,x,y,w,h):
        visual(pg,title,typ,{'Category':[cat],'Y':[val]},x,y,w,h)
    def grid(pg,title,fs,x,y,w,h):
        visual(pg,title,'tableEx',{'Values':fs},x,y,w,h)
    p=page('01  |  Inspection overview')
    for i,(title,f) in enumerate([('Model family','family'),('Age at inspection','age_band'),('Recorded mileage','mileage_band'),('Test month','month')]):slicer(p,title,'Cohorts.'+f,10+315*i,300)
    chart(p,'Initial failure rate by month','lineChart','Cohorts.month','Cohorts.Initial failure rate',10,140,750,290)
    chart(p,'Initial inspections by model','barChart','Cohorts.family','Cohorts.Initial tests',770,140,500,290)
    grid(p,'Volume, failures and rectification by model',['Cohorts.family','Cohorts.Initial tests','Cohorts.Initially failed','Cohorts.Passed after rectification','Cohorts.Initial failure rate'],10,445,1260,254)
    p=page('02  |  Fair model comparison')
    slicer(p,'Comparison year or combined','Comparison.period',10,450);slicer(p,'Comparison basis','Basis.Method',480,550)
    chart(p,'Failure rate on selected basis','barChart','Comparison.family','Comparison.Selected comparison rate',10,140,1260,268)
    grid(p,'Observed vs adjusted | pooled weights, common strata only',['Comparison.family','Comparison.Observed rate','Comparison.Standardised rate','Comparison.Share on common support','Comparison.Eligible common strata'],10,425,1260,266)
    p=page('03  |  Service priorities')
    for i,(title,f) in enumerate([('Model family','family'),('Age band','age_band'),('Mileage band','mileage_band'),('Month','month')]):slicer(p,title,'Cohorts.'+f,10+315*i,300)
    chart(p,'Affected initial tests per 1,000 by category','barChart','Category.Name','Defects.Affected per 1,000',10,140,600,550)
    grid(p,'Recorded failure items by reason | counts of items',['Reasons.category','Reasons.description','Reasons.Recorded failure items'],625,140,645,550)
    p=page('04  |  Workshop scenario')
    for i,(title,f) in enumerate([('Model family','Cohorts.family'),('Age band','Cohorts.age_band'),('Mileage band','Cohorts.mileage_band'),('Assumed inspections','Volume.Inspections')]):slicer(p,title,f,10+315*i,300)
    grid(p,'Illustrative workload from observed rates | default volume 200',['Category.Name','Cohorts.Initial tests','Defects.Affected per 1,000','Defects.Scenario inspections','Defects.Expected affected inspections'],10,140,1260,540)
    write(root/'pages/pages.json',{'$schema':FABRIC+'/report/definition/pagesMetadata/1.0.0/schema.json','pageOrder':pages,'activePageName':pages[0]})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--data',type=Path,default=ROOT/'data');parser.add_argument('--output',type=Path,default=ROOT/'powerbi')
    a=parser.parse_args();report(a.output,a.data)
