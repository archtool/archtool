'''
Created on Nov 2, 2013

@author: EHWAAL
'''


import model
from model import PlaneableItem


def exportRstFiltered(session, states_2_show, out, chapters=None):
  if not chapters:
    chapters = session.query(model.Requirement).filter(model.Requirement.Parent==None).\
               order_by(model.Requirement.Name).all()
  
  overall_estimate = 0.0
  for chapter in chapters:
    chapter_estimate = 0.0
    print >> out, '\n'.join([chapter.Name, '-'*len(chapter.Name.encode('cp1252')), ''])
    if chapter.Description:
      print >> out, chapter.Description.encode('cp1252'), '\n'
    
    for section in chapter.Children:
      print >> out, '\n'.join([section.Name, '`'*len(section.Name.encode('cp1252')), ''])
      if section.Description:
        print >> out, section.Description.encode('cp1252'), '\n'
      
      
      requirements = section.getAllOffspring()
      requirements = [r for r in requirements \
               if (len(r.StateChanges)==0 and model.REQUIREMENTS_STATES[0] in states_2_show) or \
                  (len(r.StateChanges)>0 and r.StateChanges[0].Status in states_2_show)]
      
      if len(requirements) == 0:
        continue
      
      print >> out, '.. list-table:: '
      print >> out, '   :widths: 12, 60, 10, 10, 10'
      print >> out, '   :header-rows: 1', '\n'
      
      section_estimate = 0.0
      
      print >>out, '   * - %s'%'\n     - '.join(["Name", "Description", "Prio", "Status", "Estimate"])
      
      for req in requirements:
        if req.Description:
          description = req.Description.replace('\n', '\n       ')
        else:
          description = '-'
        for sc in req.StateChanges:
          title = '%s:%s'%(sc.Status, 
                           sc.TimeStamp.strftime('%Y-%m-%d %H:%M:%S'))
          description += '\n\n       *%s*'%title
          if sc.Description:
            description += ': %s'%sc.Description.replace('\n', '\n       ')

        elements = ['   * - %s'%req.Name,
                    '     - %s'%description,
                    '     - %s'%req.Priority]
        if len(req.StateChanges) > 0:
          state = req.StateChanges[0]
          elements.append('     - %s'%state.Status)
          if state.TimeRemaining:
            elements.append('     - %s'%str(state.TimeRemaining))
            section_estimate += state.TimeRemaining
          else:
            elements.append('     - -')
        else:
          elements += ['     - %s'%model.REQUIREMENTS_STATES[0], '     - -']
        
        print >> out, '\n'.join(elements).encode('cp1252')
        
      print >> out, '\n'
      print >> out, 'Schatting voor %s: %s'%(section.Name, section_estimate), '\n'
      chapter_estimate += section_estimate
    print >> out, 'Schatting voor %s: %s'%(chapter.Name, chapter_estimate), '\n'
    overall_estimate += chapter_estimate
  print >> out, 'Totale schatting: %s'%overall_estimate, '\n'
      
      

def exportRequirementsOverview(session, out, parents=None):
  
  s = 'Requirements overzicht'
  print >> out, '\n'.join(['='*len(s), s, '='*len(s), ''])
  
  s = 'Openstaande Requirements:'
  print >> out, '\n'.join(['='*len(s), s, '='*len(s), ''])
  
  exportRstFiltered(session, set([model.REQUIREMENTS_STATES[0]]), out, parents)

  s = 'Afgeronde Requirements:'
  print >> out, '\n'.join(['='*len(s), s, '='*len(s), ''])
  
  exportRstFiltered(session, set(model.REQUIREMENTS_STATES[1:]), out, parents)

def exportRequirementQuestions(sessio, out, chapters=None):
  
  s = 'Open Questions'
  print >> out, '\n'.join(['='*len(s), s, '='*len(s), ''])

  if not chapters:
    requirements = session.query(model.Requirement).order_by(model.Requirement.Name).all()
  else:
    requirements = []
    for chapter in chapters:
      requirements += chapter.getAllOffspring()
  
  requirements = [r for r in requirements \
           if len(r.StateChanges)>0 and r.StateChanges[0].Status == 'Question']
    
  if len(requirements) == 0:
    return
    
  print >> out, '.. list-table:: '
  print >> out, '   :widths: 10, 90'
  print >> out, '   :header-rows: 1', '\n'
  
  print >>out, '   * - %s'%'\n     - '.join(["Req", "Question"])
  
  for req in requirements:
    question = req.StateChanges[0].Description
    if question:
      question = question.replace('\n', '\n       ')
    else:
      continue

    elements = ['   * - %s'%req.Name,
                '     - %s'%question]
    
    print >> out, '\n'.join(elements).encode('cp1252')


if __name__ == '__main__':
  db='sqlite:///archmodel.db'
  model.changeEngine(model.create_engine(db))
  session = model.SessionFactory()
  out = file('requirements.rst', 'w')

  exportRequirementsOverview(session, out)
