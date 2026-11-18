"""Copy-ready slide content, rendered as a selectable-text PDF."""
from pathlib import Path
import json
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
R=Path(__file__).resolve().parents[2]
S=[]
def slide(title,bullets=None,table=None,note='',source='',tag=''):
 S.append(dict(title=title,bullets=bullets or [],table=table,note=note,source=source,tag=tag))
slide("India's Urban Concentration and Emerging Growth Centres",[
 'A GHSL data engineering project using Apache Spark and Sedona',
 'Team Vector | Data Engineering at Scale',
 'Himanshu Arora - ahimanshu@iisc.ac.in',
 '[Author 2 name and email] | [Author 3 name and email] | [Author 4 name and email]'],note='Historical analysis: 1975-2020 | Accepted scope: 13 tiles; R8_C27 excluded',tag='01 / PROJECT OVERVIEW')
slide('Problem and project objectives',[
 'Measure how population and built development shifted across settlement classes.',
 'Track rural-to-urban transitions and the expansion of urban centres.',
 'Screen for smaller settlements connected to metropolitan growth or growing independently.',
 'Build a reusable pipeline that integrates different raster resolutions without losing alignment.',
 'Evaluate correctness, geospatial processing and quantitative performance.'],source='Original proposal; final requirements review')
slide('Datasets and accepted study scope',table=[
 ['Dataset','Resolution','Measurement'],['GHS-POP','100 m','Estimated residential population'],['GHS-BUILT-S','100 m','Total and non-residential built surface'],['GHS-SMOD','1 km','Settlement classification']],bullets=[
 'GHSL R2023A: ten historical epochs (1975-2020); 2025/2030 are projection tests.',
 '13 tiles x 12 epochs = 156 verified tile-years; 624 source archives.',
 'R8_C27 excluded in all epochs after retries still yielded no valid analytical cells.'],note='Results describe the accepted footprint, not complete India coverage.',source='Final handoff report; accepted coverage evidence')
slide('Architecture and data flow',[
 '<b>Acquire:</b> official JRC archives -> source manifests and integrity checks.',
 '<b>Prepare:</b> windowed raster extraction -> aligned native cells and 1 km parents.',
 '<b>Integrate:</b> Spark joins and aggregation -> validated partitioned Parquet.',
 '<b>Analyse:</b> Spark SQL -> transitions, concentration, districts and candidate events.',
 '<b>Publish:</b> independent checks -> final tables, figures and reproducible handoff.'],note='Pilot storage: real single-node HDFS. Multi-tile storage: local partitioned Parquet.',source='Phase 1 / Phase 2 completion reports; final handoff report')
slide('Grid alignment and integration rules',[
 'Use a common World Mollweide grid and keys built from grid identity, cell identity and year.',
 'Retain native 100 m population and built-surface values; sum them to aligned 1 km cells.',
 'Assign each native cell its matching-year 1 km settlement class.',
 'Preserve valid zero; represent NoData as null and flag partial coverage.',
 'Check unique keys, masks, epochs, schemas, conservation and persisted outputs.'],note='Repeating a parent category does not create independently measured 100 m settlement classes.',source='Phase 1 and Phase 2 completion reports')
slide('Apache Sedona and reliable execution',[
 'Sedona 1.9.1 executed spatial joins with Spark 3.5.6.',
 'Spatial operations checked cell containment, country coverage and district assignment.',
 'Phase 2 assigned native cell centres to matching-year SMOD parent polygons.',
 'Saved physical query plans confirm that Sedona spatial operators actually ran.',
 'Validated temporary writes, file hashes and atomic publication protect completed outputs.'],note='Sedona was evaluated on pilot workloads; national district attribution used a validated raster-centre method.',source='Phase 1 / Phase 2 reports; final requirements review')
slide('Temporal analysis and candidate screening',[
 'Use 3,280,884 coarse cells complete across all ten historical epochs.',
 'Evaluate nine adjacent five-year periods plus the full 1975-2020 period.',
 'Compute class transitions, population/built-surface changes and fixed-district summaries.',
 'Screen connected components using overlap, lineage and growth rules.',
 'Retain ambiguous, boundary-censored and below-minimum cases explicitly.'],note='Deterministic spatial rules; no ML model was trained. Candidate events require external validation.',source='Temporal / district / candidate validation; final report')
slide('Correctness checks passed at multiple levels',table=[
 ['Check','Observed result'],['Pilot spatial reference','434,363 cell assignments matched Shapely'],['All-epoch pilot integration','5,212,356 native records; zero rejected records'],['Regional raw comparison','750 cell-years; zero numeric differences; exact class agreement'],['Temporal arithmetic checks','26,870 regional cell-period comparisons; no mismatches'],['Candidate-rule checks','108,804 decisions checked; no mismatches']],note='These establish processing and rule consistency, not real-world detection precision or recall.',source='Phase 1 / Phase 2 reports; regional checks; analytical review')
slide('Performance evaluation and results',table=[
 ['Scenario','Median time','Throughput'],['Key join: 2 workers, 8 partitions','4.179 s','103,945 cells/s'],['Sedona: 1 worker, 8 partitions','7.876 s','55,152 cells/s'],['Sedona: 2 workers, 8 partitions','7.426 s','58,489 cells/s'],['Sedona: 2 workers, 32 partitions','8.990 s','48,315 cells/s']],bullets=[
 '2020 pilot: 434,363 cells; one warmup and three measured repetitions per scenario.',
 'Timer includes reads, joins, aggregation and writes; excludes startup and post-write checks.',
 'All met targets: median <=120 s, throughput >=3,500 cells/s, sampled RSS <=8 GB.'],note='Single machine: 4 physical / 8 logical CPUs, ~17.2 GB RAM. More partitions increased latency here.',source='Phase 2 completion report and benchmark evidence')
slide('Population share increased in urban classes',table=[
 ['Settlement group','1975 share','2020 share'],['Urban centres','29.4%','38.7%'],['Urban clusters','35.5%','44.3%'],['Rural classes','35.1%','16.9%']],bullets=[
 'Urban-cluster built-surface share also increased: 26.9% -> 47.2%.',
 'Shares use the same complete historical footprint.',
 'Changing settlement categories contribute to the observed change.'],note='Descriptive concentration patterns; not full-India estimates or causal evidence of migration.',source='Final handoff report; concentration.csv')
slide('Regional population and built-surface growth',table=[
 ['Study window','Population growth','Built-surface growth'],['Delhi','299.2%','42.0%'],['Mumbai vicinity*','162.1%','124.9%'],['Bengaluru','368.3%','267.8%']],bullets=[
 '1975-2020 change in 31 x 31 km study squares on the common mask.',
 'Bengaluru had the largest proportional increases among these three windows.',
 'Population grew proportionally faster than built surface in each window.'],note='Each measure uses its own 1975 baseline. *Mumbai centre adjusted for coverage; squares are not city boundaries.',source='Regional analytical review, report and validation.json')
slide('Growth and absorption candidates',table=[
 ['Event status','Count'],['Independent-growth candidate','23,317'],['Metropolitan-absorption candidate','5,085'],['Ambiguous lineage','9,317'],['Boundary censored','8,336'],['Below minimum size','3,606'],['No candidate','59,143']],note='108,804 overlapping period/component events, not unique towns. Counts depend on connectivity and growth thresholds.',source='Candidate validation and sensitivity results')
slide('Limitations and differences from the proposal',[
 'Coverage: R8_C27 remains excluded; no full-India completeness claim.',
 'Execution: engineering recovery was required; the uninterrupted-run objective was not achieved.',
 'Platforms: JRC downloads replaced Earth Engine exports; national storage is local Parquet.',
 'Scalability: local worker/partition tests do not establish multi-machine speedup.',
 'Interpretation: fixed boundary vintages and unlabelled candidate events limit conclusions.'],source='Final requirements review; final acceptance')
slide('Conclusions and next steps',[
 'Delivered a reproducible pipeline integrating population, built surface and settlement classes.',
 'Executed geospatial Spark operations and measured performance against declared targets.',
 'Completed 156 accepted tile-year integrations and all required downstream analyses.',
 'Observed increasing population concentration in urban classes on the common footprint.',
 'Next: investigate excluded coverage, validate candidates independently and benchmark a multi-node deployment.'],note='Main contribution: validated geospatial integration with explicit coverage, performance and reproducibility evidence.',source='Final report; requirements review')
slide('Suggested project demonstration',[
 '<b>1. Input contract:</b> show source provenance, grid alignment and one tile-year.',
 '<b>2. Integration:</b> show native and coarse schema, partitions and a successful validation record.',
 '<b>3. Spatial processing:</b> show a saved Sedona physical plan and validated pilot output.',
 '<b>4. Analysis:</b> show the concentration plot, district summary and candidate review output.',
 '<b>5. Evidence:</b> show benchmark comparisons and final acceptance checks.'],note='Use saved validated artifacts; no need to rerun the multi-hour pipeline during the demo.',source='SUBMISSION_README.md; phase and analysis output folders',tag='OPTIONAL / DEMO')
slide('Sources and supporting evidence',[
 '<b>Data:</b> European Commission Joint Research Centre, GHSL R2023A POP/BUILT-S V1_0 and SMOD V2_0.',
 '<b>Boundaries:</b> geoBoundaries gbOpen; country represented year 2014 and districts year 2021; ODbL 1.0.',
 '<b>Engineering:</b> Phase 1 and Phase 2 completion reports, Sedona physical plans and benchmark results.',
 '<b>Analysis:</b> final handoff report, regional analytical review and candidate validation.',
 '<b>Code:</b> github.com/himarora1/ghsl-india-urban-growth'],note='Replace author placeholders before use. Course submission requires a public repository link; visibility has not been changed.',tag='BACKUP / REFERENCES')
OUT=R/'output/pdf/GHSL_Presentation_Slide_Content.pdf';OUT.parent.mkdir(parents=True,exist_ok=True)
c=canvas.Canvas(str(OUT),pagesize=(960,540));c.setTitle('GHSL project presentation - slide-wise content');c.setAuthor('Himanshu Arora')
body=ParagraphStyle('body',fontName='Helvetica',fontSize=19,leading=26,textColor=colors.HexColor('#24333e'))
title=ParagraphStyle('title',fontName='Helvetica-Bold',fontSize=30,leading=36,textColor=colors.HexColor('#102b3a'))
small=ParagraphStyle('small',fontName='Helvetica',fontSize=12,leading=16,textColor=colors.HexColor('#526574'))
cell=ParagraphStyle('cell',parent=body,fontSize=17,leading=22)
def draw(t,style,x,y,w):
 p=Paragraph(t,style);_,h=p.wrap(w,1000);p.drawOn(c,x,y-h);return y-h
for i,s in enumerate(S,1):
 c.setFillColor(colors.HexColor('#f8fafb'));c.rect(0,0,960,540,fill=1,stroke=0)
 c.setFillColor(colors.HexColor('#247e88'));c.rect(48,490,34,5,fill=1,stroke=0)
 c.setFont('Helvetica',11);c.drawString(94,489,s['tag'] or f'{i:02d} / GHSL PROJECT')
 y=draw(s['title'],title,48,465,864)-24
 if s['table']:
  rows=s['table'];n=len(rows[0]);widths=[864*.50]+[864*.50/(n-1)]*(n-1)
  t=Table([[Paragraph(v,cell) for v in row] for row in rows],colWidths=widths)
  t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcebed')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#edf2f4')]),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LEFTPADDING',(0,0),(-1,-1),10)]))
  _,ht=t.wrap(864,1000);t.drawOn(c,48,y-ht);y-=ht+16
 for b in s['bullets']:
  c.setFillColor(colors.HexColor('#247e88'));c.circle(54,y-10,3,fill=1,stroke=0)
  y=draw(b,body,70,y,840)-12
 if s['note']:
  note=Paragraph(s['note'],small);_,nh=note.wrap(864,1000)
  assert y>=63+nh,(i,y,nh)
  note.drawOn(c,48,63)
 assert y>62,(i,y)
 c.setFont('Helvetica',10);c.setFillColor(colors.HexColor('#657784'));c.drawString(48,26,s['source'] or 'Team Vector | Presentation content');c.drawRightString(912,26,f'{i} / {len(S)}');c.showPage()
c.save()
(R/'output/pdf/GHSL_Presentation_Slide_Content.json').write_text(json.dumps(S,indent=2)+'\n')
print(OUT)
