'''
Created on Nov 24, 2013

@author: EHWAAL
'''

import pylab
import numpy as np
import model
from model import Worker, Project, PlannedEffort, PlaneableStatus, PlaneableItem
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg

def getWorkRemaining(project, session):
  ''' Determine how much work was remaining at each stage in the project.
  
      Returns a tuple (times, work), where work is a dictionary with (prio, [remaining]) tuples.
      times is measured in weeks since project start.
      Remaining is a list with for each time the amount of workdays for the particular priority.
  '''
  # Determine all requirements relevant for this project
  requirements = [req for req in project.AItems if req.ItemType=='requirement']
  offspring = list(requirements)
  for r in requirements:
    PlaneableItem.getAllOffspring(r, offspring)
  
  all_ids = [r.Id for r in offspring]
  all_requirements = offspring
  print all_ids
  
  # Find all state changes for relevant requirements, sorted by date
  all_changes = session.query(PlaneableStatus).\
                        filter(PlaneableStatus.Planeable.in_(all_ids)).\
                        order_by(PlaneableStatus.TimeStamp)
                        
  # Determine the times vector
  times = [change.TimeStamp.toordinal() for change in all_changes]
  # Determine the time remaining
  all_points = {}
  for prio in model.PRIORITIES:
    points = []
    # Count only Functional requirements of the right priority.
    ids = [r.Id for r in all_requirements if r.Priority == prio and r.Type==model.REQ_TYPES[0]]
    remaining = {i:0.0 for i in ids}    # keep track of work remaining for each requirement
    for change in all_changes:
      if change.Planeable in ids:
        if change.isOpen():
          remaining[change.Planeable] = change.TimeRemaining
        else:
          remaining[change.Planeable] = 0.0
      points.append(sum(remaining.values()))
    all_points[prio] = points

  # Convert the date ordinal number to a week number since project start.
  times = [(t-project.FirstWeek.dt.toordinal())/7.0 for t in times]
  
  return times, all_points


def getEffortSpent(project, session):
  ''' Determine the effort spent on the project.
  
      returned is a tuple (times, spent). Both values are lists of equal length.
      times are in weeks since project start.
  '''
  efforts = session.query(PlannedEffort).\
                    filter(PlannedEffort.Project==project.Id).\
                    order_by(PlannedEffort.Week).all()
  times = []
  current_week = None
  sums = []
  current_sum = 0.0
  for e in efforts:
    if e.Week != None:
      if e.Week != current_week:
        times.append(e.Week)
        current_week = e.Week
        sums.append(current_sum)
        current_sum = e.Hours
      else:
        current_sum += e.Hours
  sums.append(current_sum)
  times.append(e.Week)
    
  # Convert the date ordinal number to a week number since project start.
  times = [(t.dt.toordinal()-project.FirstWeek.dt.toordinal())/7.0 for t in times]
  # Convert the sums (which are in hours) into mandays
  sums = [s/8.0 for s in sums]
  csum = pylab.cumsum(sums)
  
  return times, csum
      


def plotEarnedValue(project, session, fig):
  ''' The earned value calculation is based on requirements that are completed.
  '''
  ax1 = fig.add_subplot(211)


  # Create the effort spent graph
  times, effort_spent = getEffortSpent(project, session)
  print 'effort spent', len(times), len(effort_spent)
  ax1.plot(times, effort_spent)

  
  # Create the work-remaining graph
  times, points = getWorkRemaining(project, session)
  # Colors for Must, Should, Could and Would.
  colors = [(1.0, 0, 0), (1.0, 1.0, 0), (0, 1, 0), (0, 0, 1)]
  prev_counts = np.zeros(len(times))
  colors = list(reversed(colors))
  points = [points[prio] for prio in reversed(model.PRIORITIES)]
  lines = []
  for index, color in enumerate(colors):
    print 'index:', index, 
    print len(points[index])
    print len(times)
    l = ax1.plot(times, points[index], color=color) #, bottom=prev_counts)
    lines.append(l)
    prev_counts += points[index]
    
  pylab.xlabel('week')
  #pylab.ylabel('Work Remaining')
  pylab.title('Burn-Down Graph')
  pylab.show()


if __name__ == '__main__':
  session = model.connectSession('sqlite:///archmodel.db')
  project = session.query(Project).filter(Project.Name=='DRIS Helmond').first()
  figure = pylab.Figure()
  plotEarnedValue(project, session, figure)

