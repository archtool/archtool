'use strict';


function determineUpdate(oldvalues, newvalues){
    var aProps = Object.getOwnPropertyNames(oldvalues);
    var bProps = Object.getOwnPropertyNames(newvalues);
    var update = {};
    var not_equal = false;
    for (var i=0; i<aProps.length; i++){
        var propName = aProps[i];
        if (oldvalues[propName] != newvalues[propName]){
            update[propName] = newvalues[propName];
            not_equal = true;
        }
    }
    if (not_equal) {
        // Ensure the record id is also in the diff: this is required in the update.
        update.id = newvalues.id;
        return update;
    }
    return false;
}


/* Controllers */
var archtoolApp = angular.module("archtoolApp", ['ngResource', 'ui.bootstrap', 'ui.tree',
                                 'bgDirectives', 'ng-context-menu']);
archtoolApp.config(function($resourceProvider) {
  $resourceProvider.defaults.stripTrailingSlashes = false;
});


archtoolApp.config(['$httpProvider', function($httpProvider) {
    $httpProvider.defaults.xsrfCookieName = 'csrftoken';
    $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
}]);

archtoolApp.factory("ItemDetailsResource", function ($resource) {
    return $resource("/api/planeableitems/:id/?itemtype=:it", {'id':'@id', 'it':'@it'},
                                {'update': {'method':'PATCH'}});
  });


archtoolApp.controller("SvgEditor", function ($scope, $rootScope, $resource) {
  var viewItems = $resource("/api/viewitems/:view_id/", {
        'view_id':function(){return $rootScope.currentView.id;}},
        {'query':  {method:'GET', isArray:false},});

  var anchorDetails = $resource("/api/viewitemdetails/:anchortype/", {'anchortype':'@anchortype'});

  $scope.blocks = [];
  /*
    {'Id':1,
     'x': 20,
     'y': 20,
     'name': "Is",
     'width': 100,
     'height': 50,
     'style': 'archblock'
    },
    {'Id':2,
     'x': 100,
     'y': 100,
     'name': "Lief",
     'width': 100,
     'height': 50,
     'style': 'archblock'
    },
    {'Id':3,
     'x': 0,
     'y': 100,
     'name': "Mieke",
     'width': 100,
     'height': 50,
     'style': 'archblock'
    }
  ]; */

  $scope.lines = [];
  var line_2_blocks = {};
  /*
    {'start':$scope.blocks[0],
     'end':$scope.blocks[1]},
    {'start':$scope.blocks[2],
     'end':$scope.blocks[0]}
  ];*/

  $scope.selected = [];
  $scope.last_pos = [0,0];
  $scope.drag = false;

  $rootScope.$watch("currentView", function(newval, oldval){
      if (newval != null && newval != oldval) {
        var items = viewItems.query();
        items.$promise.then(function(result){
          line_2_blocks = {};
          $scope.blocks = result.blocks;
          update_line_2_blocks(result.connections);
          $scope.lines  = result.connections;
          $scope.actions = result.actions;
          $scope.annotations = result.annotations;
        });
      }
  });

  function update_line_2_blocks(lines) {
    for (var i=0; i<lines.length; i++) {
      var line = lines[i];
      var start = null;
      var end = null;
      for (var j=0; j<$scope.blocks.length; j++) {
        var block = $scope.blocks[j];
        if (line.start == block.id) {
          start = block;
        }
        if (line.end == block.id) {
          end = block;
        }
      }
      line_2_blocks[line] = [start, end];
    }
  }

  $scope.onRightClick = function(evt) {
  };

  $scope.onMouseDown = function(evt, obj) {
    $scope.last_pos = [evt.x, evt.y];
    $scope.drag = true;
    console.log("Mouse down " + $scope.selected.length);
  };

  $scope.onMouseMove = function(evt, obj) {
    if ($scope.drag && $scope.selected.length > 0) {
      console.log("Mouse Move ");
      var delta_x = evt.x - $scope.last_pos[0];
      var delta_y = evt.y - $scope.last_pos[1];

      angular.forEach($scope.selected, function(obj) {
        obj.x += delta_x;
        obj.y += delta_y;
      });
    };
    $scope.last_pos = [evt.x, evt.y];
  };

  $scope.onMouseUp = function(evt, obj) {
    console.log("Mouse up" + obj);
    $scope.drag = false;
  };

  $scope.onClick = function(obj, event) {
    if (event.shiftKey) {
      $scope.selected.push(obj);
    } else {
      $scope.selected = [obj];
    }
    event.handled = true;
  };

  $scope.clearSelection = function(event) {

    $scope.selected = [];
  };

  $scope.getX1 = function(line) {
    var start = line_2_blocks[line][0];
    return start.x + start.width/2;
  };
  $scope.getY1 = function(line) {
    var start = line_2_blocks[line][0];
    return start.y + start.height/2;
  };
  $scope.getX2 = function(line) {
    var end = line_2_blocks[line][1];
    return end.x + end.width/2;
  };
  $scope.getY2 = function(line) {
    var end = line_2_blocks[line][1];
    return end.y + end.height/2;
  };

  $rootScope.addBlock = function(planeable) {
    var item = new anchorDetails({'x': 20,
     'y': 20,
     'view': $rootScope.currentView.id,
     'name': planeable.name,
     'width': 100,
     'height': 50,
     'anchortype': 'block',
     'planeable': planeable.id,
     'ismultiple': false});

    item.$save(function(data){
      $scope.blocks.push(data);
    });
  };

  $scope.connectBlocks = function() {
    var start = $scope.selected[0];
    var end = $scope.selected[1];
    var item = new anchorDetails({
     'view': $rootScope.currentView.id,
     'anchortype': 'line',
     'start': start.id,
     'end': end.id
     });

    item.$save(function(data){
      update_line_2_blocks([data]);
      $scope.lines.push(data);
    });
  }

});


archtoolApp.controller('SystemCtrl', function ($scope, $rootScope, $resource, $modal) {
    var Systems = $resource('/api/systems/');

    $scope.systems = Systems.query();
    $rootScope.currentSystem = null;

    $scope.newSystem = function() {
      var url = "/api/editors/?itemtype=system";
      var modalWindow = $modal.open({
        animation: false,
        templateUrl: url,
        controller: "ModalEditor",
        resolve:{'context':function(){return {
            'url': url,
            'Resource': Systems,
            'title': 'Add Model',
            'initial': {}
        };}}
      });

      modalWindow.result.then(function (newSystem) {
        $scope.systems.push(newSystem);
        $rootScope.currentSystem = newSystem;
      });
    };
 });


archtoolApp.controller("ModalEditor", function($scope, $modalInstance, context){
    $scope.item = new context.Resource(context.initial);
    $scope.title = context.title;
    $scope.templateUrl = context.url;

    $scope.submit = function(e) {
      var form = angular.element(e.target.form);
      form.submit();
    };

    $scope.ok = function() {
      $scope.item = $scope.item.$save(function(data){
        $scope.item.id = data.id;
      });
      $modalInstance.close($scope.item);
    };
    $scope.cancel = function() {
      $modalInstance.dismiss('cancel');
    };
});


archtoolApp.controller("DetailsController", function($scope, $rootScope, ItemDetailsResource){
    $scope.templateUrl = null;
    $scope.item = null;
    $scope.original_item = null;

    $rootScope.$watch("currentSelection", function(newval, oldval){
        if (newval != null) {
          $scope.templateUrl = '/api/editors/?itemtype='+newval.itemtype;
          if ($scope.item && $scope.original_item) {
            var currentvalue = $scope.item.toJSON();
            var delta = determineUpdate($scope.original_item, currentvalue);
            if (delta) {
              delta.it = newval.itemtype;
              ItemDetailsResource.update(delta);
            }
          }
          $scope.item = newval;
          $scope.original_item = newval.toJSON();
        }
    });
});


archtoolApp.controller("ViewsList", function($scope, $rootScope, $resource){
    var viewListResource = $resource("/api/planeableitems/?itemtype=view&system=:system", {
        'system':function(){return $rootScope.currentSystem.id;}});
    $scope.allViews = [];
    $rootScope.currentView = null;

    /** Evaluate the query when either the itemtype or the system changes */
    $rootScope.$watch('currentSystem', function(newvalue, oldvalue){
        if (newvalue != null) {
          var items = viewListResource.query();
          items.$promise.then(function (result) {
              $scope.allViews = result;
          });
        }
    });
});


archtoolApp.controller("ItemsList", function($scope, $rootScope, $resource, $modal,
                                             $document, ItemDetailsResource){
    var itemTypes = $resource("/api/planeabletypes/");
    $scope.itemTypes = itemTypes.query();

    var Priorities = $resource("/api/priorities/");
    $rootScope.priorities = Priorities.query();

    var ReqTypes = $resource("/api/reqtypes/");
    $rootScope.reqTypes = ReqTypes.query();

    $scope.currentItemType = null;
    $scope.itemTypes.$promise.then(function (result) {
        $scope.itemTypes = result;
        $scope.currentItemType = result[0];
    });

    $rootScope.currentSelection = null;

    var Items = $resource("/api/planeableitems/?system=:system&itemtype=:itemtype", {
        'system':function(){return $rootScope.currentSystem.id;},
        'itemtype':function(){return $scope.currentItemType;}
    });

    $scope.rootItems = [];

    /** Evaluate the query when either the itemtype or the system changes */
    $rootScope.$watch('currentSystem', function(newvalue, oldvalue){
        if (newvalue != null) {
          var items = Items.query();
          items.$promise.then(function (result) {
              orderItems(result);
          });
        }
    });
    $scope.$watch('currentItemType', function(newvalue, oldvalue){
        if ($rootScope.currentSystem != null) {
            var items = Items.query();
            items.$promise.then(function (result) {
                orderItems(result);
            });
        }
    });

    var orderItems = function(items){
        /** Create an associative array with item ID as key. */
        var ar = {}
        for (var i=0; i<items.length; i++){
            ar[items[i].id] = items[i];
            /* Also initialise the 'children' field. */
            items[i].children = [];
        }

        /** Re-organise the items according to their hierarchy.
            Also find root items. */
        var rootItems = [];
        for (var i=0; i<items.length; i++){
            var item = items[i];
            if (!item.parent) {
                rootItems.push(item);
            } else {
                /* Get the parent item */
                var parent_id = item.parent;
                var parent = ar[parent_id];
                /* Add this item as a child. */
                parent.children.push(item);
                /* TODO: Sort the children according to their order. */
            }
        }
        $scope.rootItems = rootItems;
        /*$scope.items = items;*/
    };

    $scope.removeItem = function(scope, item) {
      ItemDetailsResource.remove(item);
      scope.remove();
    };

    $scope.toggle = function(scope) {
      scope.toggle();
    };

    function getInitialData(item) {
        parent = null;
        if (item != null) {
            parent = item.id;
        }
        var order = item ? item.length : $scope.rootItems.length;
        return {'parent':parent,
                'system':$rootScope.currentSystem.id,
                'itemtype':$scope.currentItemType,
                'order':order};
    };

    $scope.newItem = function(item) {
      if (!$rootScope.currentSystem){
          alert('First select a model');
          return;
      }
      var url = "/api/editors/?itemtype="+$scope.currentItemType;
      var modalWindow = $modal.open({
        animation: false,
        templateUrl: url,
        controller: "ModalEditor",
        resolve:{'context':function(){return {
            'url': url,
            'Resource': Items,
            'title': 'Add '+$scope.currentItemType,
            'initial': getInitialData(item)
        };}}
      });

      modalWindow.result.then(function (newItem) {
        if (item) {
          item.children.push(newItem);
        } else {
          newItem.children = [];
          $scope.rootItems.push(newItem);
        };
      });
    };

    var getRootNodesScope = function() {
      return angular.element(document.getElementById("tree-root")).scope();
    };

    $scope.collapseAll = function() {
      var scope = getRootNodesScope();
      scope.collapseAll();
    };

    $scope.expandAll = function() {
      var scope = getRootNodesScope();
      scope.expandAll();
    };

    $scope.viewItem = function(item) {
      var details = ItemDetailsResource.get({id:item.id, it:item.itemtype}, function() {
        $rootScope.currentSelection = details;
      });
    };

    $scope.treeOptions = {'dragStop':function(event){
        /** An item was dropped in a new location. Check if anything was changed,
        and update the relevant items if there was. */
        updateOrder($scope.rootItems, null);
    }};

    function updateOrder(children, parent) {
        var i=0;
        for (i=0; i<children.length; i++) {
            var child = children[i];
            if (child.parent != parent) {
                /* The parent has changed: update the item */
                child.parent = parent;
                ItemDetailsResource.update({'id':child.id, 'it':child.itemtype, 'parent':parent});
            }
            if (child.order != i) {
                /* The ordering has changed: update the item */
                child.order = i;
                ItemDetailsResource.update({'id':child.id, 'it':child.itemtype, 'order':child.order});
            }
            /* Make a recursive call to check the children */
            updateOrder(child.children, child.id);
        }
    };


    $scope.contextMenu = function(event, node) {
        var x = event.clientX;
        var y = event.clientY;

        var el = document.getElementById("dropdown-menu");
        el.style.visibility = "visible";
        el.style.top = y+'px';
        el.style.left = x+'px';

        $scope.planeable = node;

        function handleClickevent(event) {
          var t = event.target;
          while (t) {
            t = t.parentElement;
            if (t === el) {
              return;
            }
          }
          $document.unbind('click', handleClickevent);
          el.style.visibility = 'hidden';
        }

        $document.bind('click', handleClickevent);
    }
});


archtoolApp.directive('ngRightClick', function($parse) {
    return function(scope, element, attrs) {
        var fn = $parse(attrs.ngRightClick);
        element.bind('contextmenu', function(event) {
            scope.$apply(function() {
                event.preventDefault();
                fn(scope, {$event:event});
            });
        });
    };
});

