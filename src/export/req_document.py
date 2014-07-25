'''
Created on Nov 2, 2013

@author: EHWAAL
'''

import re
import StringIO
import model
from model import PlaneableItem
from model import config
from docutils.core import publish_string, default_description



TABLE_COLUMNS = ["Name", "Description"]

ENCODING = 'utf-8'

TABLE_HEADER = '''
.. list-table:: 
   :widths: 10 90
   :header-rows: 1
   
'''

TABLE_START = '''
   * - '''

TABLE_SEPARATOR = '''
     - '''



REQ_NR = re.compile('([0-9a-zA-Z\.]*)[^\.]')

def cmpRequirements(a, b):
  ''' Compare requirements on their names '''
  na, nb = a.Name, b.Name
  na = REQ_NR.match(na).groups()[0]
  nb = REQ_NR.match(nb).groups()[0]
  
  if na == '' or nb == '':
    return cmp(a.Name, b.Name)
  
  aparts = na.split('.')
  bparts = nb.split('.')
  
  for i in range(min([len(aparts), len(bparts)])):
    # Skip this check if the parts are the same.
    if aparts[i] == bparts[i]:
      continue
    if aparts[i].isnumeric() and bparts[i].isnumeric():
      # Compare as integers
      return cmp(int(aparts[i]), int(bparts[i]))
    # Compare as strings
    return cmp(aparts[i], bparts[i])
  # Compare on length...
  return cmp(len(aparts), len(bparts))
  

def renderChapterHead(item, sep='-', also_above=False):
  name = item.Name.encode(ENCODING)
  lines = ['']
  if also_above:
    lines.append(sep*len(name))
  lines += [name, sep*len(name), '']
  if item.Description:
    lines.append(item.Description.encode(ENCODING))
  return '\n'.join(lines)


def renderSectionHead(item):
  return renderChapterHead(item, '`')

def renderRequirementsTable(items):
  result = TABLE_HEADER + TABLE_START + TABLE_SEPARATOR.join(TABLE_COLUMNS)
  
  for item in items:
    values = [getattr(item, k).encode(ENCODING).replace('\n', '\n       ') for k in TABLE_COLUMNS]
    result += TABLE_START + TABLE_SEPARATOR.join(values)
    
  return result

def exportRequirementsDocument(session, requirement_name):
  top_items = session.query(model.Requirement).\
                     filter(model.Requirement.Name==requirement_name).\
                     all()
                    
  if len(top_items) == 0:
    raise RuntimeError('Could not find %s, sorry'%requirement_name)
  top_item = top_items[0]
  
  out = StringIO.StringIO()
  
  print >> out, renderChapterHead(top_item, '=', True)
  for chapter in sorted(top_item.Children, cmp=cmpRequirements):
    print >> out, renderChapterHead(chapter)
    
    for section in sorted(chapter.Children, cmp=cmpRequirements):
      print >> out, renderSectionHead(section)
      # TODO: make this a recursive query to catch sub-requirements
      print >> out, renderRequirementsTable(sorted(section.Children, cmp=cmpRequirements))
  
  html = publish_string(out.getvalue(), writer_name='html')

  with open('%s/%s.html'%(config.getConfig('export_dir'), top_item.Name), 'w') as f:
    f.write(html)
