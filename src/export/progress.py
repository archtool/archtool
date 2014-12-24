"""
Produce a report that shows the progress with regards to a planneable item set.

"""
__author__ = 'ehwaal'

import datetime
import pylab
from model import REQUIREMENTS_STATES, OPEN_STATES, REQ_TYPES, PlaneableStatus, Requirement


# TODO: Take into account the Creation time for planeableitems.


colors = [(1.0, 0, 0), (1.0, 1.0, 0), (0, 1, 0), (0, 0, 1), (0, 0, 0)]
fillcolors = [tuple([(i+1.0)/2.0 for i in color]) for color in colors]


def makeBurnDownChart(session, items, ax):
  """ Create a burn down graph, and return it as an SVG image inside a StringIO stream.
  """
  # Get all the StateChange items
  PRIO_INDEX = {'Must':0, 'Should':1, 'Could':2, 'Would':3}
  changes = session.query(PlaneableStatus).all()
  changes = sorted(changes, key=lambda x: x.TimeStamp)

  prio_counts = [0, 0, 0, 0, 0] # [Must, Should, Could, Would, Closed]
  for it in items:
    index = PRIO_INDEX[it.Priority]
    prio_counts[index] += 1

  prev_states = dict([(i.Id, REQUIREMENTS_STATES.OPEN) for i in items])
  start = changes[0].TimeStamp.toordinal()

  # Make an initial count of all items
  counts = [0 for i in range(5)]
  for it in items:
    index = PRIO_INDEX[it.Priority]
    counts[index] += 1
  all_counts = [counts]
  time_line = [0.0]

  for change in changes:
    if change.Planeable not in prev_states:
      continue
    prev_state = prev_states[change.Planeable]
    if prev_state in OPEN_STATES:
      index = PRIO_INDEX[change.theItem.Priority]
    else:
      index = 4
    prio_counts[index] -= 1

    if change.Status in OPEN_STATES:
      index = PRIO_INDEX[change.theItem.Priority]
    else:
      index = 4
    prio_counts[index] += 1

    all_counts.append(list(prio_counts))
    time_line.append(change.TimeStamp.toordinal()-start)

  # Add a final marker at 'NOW'.
  all_counts.append(prio_counts)
  time_line.append(datetime.date.today().toordinal()-start)

  ydata = pylab.array(all_counts)
  ydata = ydata.cumsum(axis=1)

  labels = ['Must', 'Should', 'Could', 'Would', 'Completed']

  for i in range(5):
    ax.plot(time_line, ydata[:,i], color=colors[i], linewidth=3, label=labels[i])
    bottom = ydata[:, i-1] if i>0 else pylab.zeros(len(time_line))
    ax.fill_between(time_line, ydata[:,i], bottom, facecolor=fillcolors[i])

  ax.set_xlabel('Days since project start')
  ax.set_ylabel('Open and closed work items')
  ax.legend(loc='bottom left', shadow=True)





def makeEarnedValueChart(project):
  pass


def createProgressReport(session, item):
  # Determine the work items to take into account.
  items = parent_item.getAllOffspring()
  # When working with requirements, only take the functional requirements into account
  if isinstance(parent_item, Requirement):
    items = [it for it in items if it.Type == REQ_TYPES.FUNCTIONAL]

  fig, (ax1) = pylab.subplots(1, 1)
  makeBurnDownChart(session, items, ax1)
  fig.savefig('progress.svg', format='svg')

  # Determine the time remaining
  remaining = [it for it in items if it.StateChanges and it.StateChanges[0].Status in OPEN_STATES]
  time_remaining = sum([it.StateChanges[0].TimeRemaining for it in remaining if it.StateChanges])


