


Planning View
====================

`
**Determine how a project is tracked**: The progress of a project is tracked by the planeable items
that are associated with a project. For example, a certain set of requirements or use cases can
be associated with a project. All child items are also taken into account, so it is usually enough
to associate the project with just one planeable. The association is done as described in
`Planeable Details Editor`_.

If the project is associated with a Requirement, only the Functional Requirements are taken into
account for determining progress.


**Estimate Overview**: can be shown and edited by right-clicking on a project.
The estimate overview is shown as the estimate for each planing item for each week.
Weeks for which there is no planning are shown with a dash.


Planeable Details Editor
=============================

Planeable Cross-Links
-----------------------

When a `Planeable Item`_ is selected, the planeable details editor is shown in the details window.
This details editor allows editing of the specific fields associated planeable item, but also
allows cross links to be created between various planeable items. Thus, for example a Requirement
can be associated with the Use Cases that implement this requirement. Also, a project can be
associated with the requirements or Use Cases that need to be implemented as part of the project.

An association has two sides, the A-role and the B-role. This assumes a hierarchy, such as:
Project -> Requirements -> Use Cases -> Function Points, but the user can create any hierarchy.

Associations are created from the A-role to the B-role. The editor shows the associations in two
columns. The associations where the current planeable has the A-role, and those where it has the
B-role. The list with the A-role can be edited, using the '+' and '-' buttons.

Planeable Status
------------------

A 'Status' can be associated with a planeable item. Details related to the implementation of the
planeable can be changed, such as the worker to which the planeable is assigned, whether the
planeable has been implemented or not, and the current estimate for the work remaining. A timestamp
is linked to the state change. A history of these status changes is shown in the details editor.
Also, new status changes can be added and existing status changes can be edited.
Editing does not change the status change timestamp.