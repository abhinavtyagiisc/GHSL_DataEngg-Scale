"""Editable DOCX counterpart generated from the same report source content."""
from pathlib import Path
from html.parser import HTMLParser
import ast,io
import fitz
from docx import Document
from docx.shared import Pt,Cm,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH,WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from reportlab.pdfgen.canvas import Canvas
ROOT=Path(__file__).resolve().parents[2]
source=(ROOT/'analysis/scripts/build_final_report.py').read_text()
module=ast.parse(source)
start=next(i for i,n in enumerate(module.body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='h')
end=next(i for i,n in enumerate(module.body) if isinstance(n,ast.FunctionDef) and n.name=='footer')
g={'__file__':str(ROOT/'analysis/scripts/build_final_report.py')}
exec(compile(ast.Module(body=module.body[:start],type_ignores=[]),'report_setup','exec'),g)
doc=Document();sec=doc.sections[0];sec.page_width=Cm(21);sec.page_height=Cm(29.7)
sec.top_margin=sec.bottom_margin=sec.left_margin=sec.right_margin=Cm(2.5);sec.footer_distance=Cm(1.8)
for name in ['Normal','Title','Heading 1','Heading 2','Caption','Footer']:
 s=doc.styles[name];s.font.name='Times New Roman';s.font.size=Pt(10);s.font.color.rgb=RGBColor(0,0,0)
 s.paragraph_format.line_spacing=Pt(12);s.paragraph_format.space_after=Pt(6);s.paragraph_format.space_before=Pt(0)
for name in ['Heading 1','Heading 2']:doc.styles[name].font.bold=True;doc.styles[name].paragraph_format.space_before=Pt(8)
doc.styles['Title'].font.bold=True
class Rich(HTMLParser):
 def __init__(self,p):super().__init__();self.p=p;self.bold=False;self.italic=False
 def handle_starttag(self,t,attrs):
  if t=='b':self.bold=True
  if t=='i':self.italic=True
  if t=='br':self.p.add_run().add_break()
 def handle_endtag(self,t):
  if t=='b':self.bold=False
  if t=='i':self.italic=False
 def handle_data(self,t):
  r=self.p.add_run(t);r.bold=self.bold or self.p.style.name in ['Title','Heading 1','Heading 2'];r.italic=self.italic;r.font.name='Times New Roman';r.font.size=Pt(10)
pending=False
count=0
def para(text,style=None):
 global pending
 p=doc.add_paragraph();p.style='Normal';p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
 if style is g.get('caption'):p.alignment=WD_ALIGN_PARAGRAPH.LEFT
 if pending:p.paragraph_format.page_break_before=True;pending=False
 Rich(p).feed(text);return p
def heading(text):
 global count
 p=para(text);p.style='Title' if count==0 else 'Heading 2' if text[:3].replace('.','').isdigit() and '.' in text[:3] else 'Heading 1';p.alignment=WD_ALIGN_PARAGRAPH.LEFT;p.paragraph_format.keep_with_next=True
 for r in p.runs:r.bold=True
 count+=1
def page():
 global pending
 pending=True
def table(rows,widths):
 t=doc.add_table(rows=0,cols=len(widths));t.autofit=False
 for col,w in zip(t.columns,widths):col.width=Pt(w)
 for i,row in enumerate(rows):
  cells=t.add_row().cells
  for j,txt in enumerate(row):
   c=cells[j];c.width=Pt(widths[j]);pr=c._tc.get_or_add_tcPr();mar=OxmlElement('w:tcMar')
   for edge in ['top','bottom','left','right']:
    el=OxmlElement('w:'+edge);el.set(qn('w:w'),'80');el.set(qn('w:type'),'dxa');mar.append(el)
   pr.append(mar)
   if i==0:sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'E9EFF3');pr.append(sh)
   p=c.paragraphs[0];p.paragraph_format.space_after=Pt(0);p.paragraph_format.line_spacing=Pt(12);Rich(p).feed(str(txt))
  trpr=t.rows[-1]._tr.get_or_add_trPr();trpr.append(OxmlElement('w:cantSplit'))
  if i==0:trpr.append(OxmlElement('w:tblHeader'))
 borders=OxmlElement('w:tblBorders')
 for edge in ['top','bottom','left','right','insideH','insideV']:
  el=OxmlElement('w:'+edge);el.set(qn('w:val'),'single');el.set(qn('w:sz'),'3');el.set(qn('w:color'),'D9D9D9');borders.append(el)
 t._tbl.tblPr.append(borders)
 p=doc.add_paragraph();p.paragraph_format.space_after=Pt(0);p.paragraph_format.line_spacing=Pt(4);p.add_run().font.size=Pt(4)
class Story:
 def append(self,obj):
  if isinstance(obj,g['Chart']):
   stream=io.BytesIO();c=Canvas(stream,pagesize=(obj.width,obj.height));obj.canv=c;obj.draw();c.save();pdf=fitz.open(stream=stream.getvalue(),filetype='pdf');png=pdf[0].get_pixmap(matrix=fitz.Matrix(3,3)).tobytes('png')
   p=doc.add_paragraph();p.paragraph_format.space_after=Pt(0);p.paragraph_format.keep_with_next=True;p.add_run().add_picture(io.BytesIO(png),width=Pt(obj.width),height=Pt(obj.height))
  else:raise TypeError(type(obj))
g.update(p=para,h=heading,page=page,table=table,story=Story())
exec(compile(ast.Module(body=module.body[start:end],type_ignores=[]),'report_content','exec'),g)
p=sec.footer.paragraphs[0];p.style='Footer';p.paragraph_format.space_after=Pt(0);p.add_run('Team Vector | GHSL final project report\t');p.paragraph_format.tab_stops.add_tab_stop(Cm(16),WD_ALIGN_PARAGRAPH.RIGHT)
r=p.add_run();f=OxmlElement('w:fldSimple');f.set(qn('w:instr'),'PAGE');r._r.addnext(f)
doc.core_properties.title="India's Urban Concentration and Emerging Growth Centres using GHSL";doc.core_properties.author='Himanshu Arora'
out=ROOT/'output/docx/GHSL_Final_Project_Report.docx';out.parent.mkdir(parents=True,exist_ok=True);doc.save(out);print(out)
