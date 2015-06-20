'use strict';

/* Controllers */
var archtoolApp = angular.module("archtoolApp", ['ngResource', 'ui.bootstrap', 'ui.tree']);
archtoolApp.config(function($resourceProvider) {
  $resourceProvider.defaults.stripTrailingSlashes = false;
});

archtoolApp.controller("SvgEditor", function ($scope) {
  $scope.blocks = [
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
  ];

  $scope.lines = [
    {'start':$scope.blocks[0],
     'end':$scope.blocks[1]},
    {'start':$scope.blocks[2],
     'end':$scope.blocks[0]}
  ];

  $scope.selected = [];
  $scope.last_pos = [0,0];
  $scope.drag = false;

  $scope.onMouseDown = function(evt, obj) {
    $scope.last_pos = [evt.x, evt.y];
    $scope.selected = [obj];
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

  $scope.onClick = function(obj) {
  };

  $scope.getX1 = function(line) {
    return line.start.x + line.start.width/2;
  };
  $scope.getY1 = function(line) {
    return line.start.y + line.start.height/2;
  };
  $scope.getX2 = function(line) {
    return line.end.x + line.end.width/2;
  };
  $scope.getY2 = function(line) {
    return line.end.y + line.end.height/2;
  };

});


archtoolApp.controller('SystemCtrl', function ($scope, $rootScope, $resource, $modal) {
    var Systems = $resource('/api/systems/');

    $scope.systems = Systems.query();
    $rootScope.currentSystem = null;

    $scope.newSystem = function() {

      var modalWindow = $modal.open({
        animation: false,
        templateUrl: "/api/editortemplate/system",
        controller: "ModalSystemEditor",
        resolve:{'Resource':function(){return Systems;}}
      });

      modalWindow.result.then(function (newSystem) {
        $scope.systems.push(newSystem);
        $rootScope.currentSystem = newSystem;
      });
    };
 });


archtoolApp.controller("ModalSystemEditor", function($scope, $modalInstance, Resource){
    $scope.system = new Resource();

    $scope.ok = function() {
      $scope.system = $scope.system.$save(function(data){
        $scope.system.id = data.id;
      });
      $modalInstance.close($scope.system);
    };
    $scope.cancel = function() {
      $modalInstance.dismiss('cancel');
    };
});


archtoolApp.controller("ItemsList", function($scope, $rootScope, $resource, $modal){
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

    var Items = $resource("/api/planeableitems/?system=:system&itemtype=:itemtype", {
        'system':function(){return $rootScope.currentSystem.id;},
        'itemtype':function(){return $scope.currentItemType;}
    });

    var ItemDetails = $resource("/api/planeableitems/:id/", {'id':'@id'},
                                {'update': {'method':'PATCH'}});

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
      ItemDetails.remove(item);
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

    $scope.newSubItem = function(item) {
      var modalWindow = $modal.open({
        animation: false,
        templateUrl: "/api/editortemplate/"+item.itemtype,
        controller: "ModalItemEditor",
        resolve:{'Resource':function(){return Items;},
                 'Initial':function(){return getInitialData(item);}
                }
      });

      modalWindow.result.then(function (newItem) {
        item.children.push(newItem);
      });
    };

    $scope.newRootItem = function() {
      if (!$rootScope.currentSystem){
          alert('First select a model');
          return;
      }
      var modalWindow = $modal.open({
        animation: false,
        templateUrl: "/api/editortemplate/"+$scope.currentItemType,
        controller: "ModalItemEditor",
        resolve:{'Resource':function(){return Items;},
                 'Initial':function(){return getInitialData(null);}
                }
      });

      modalWindow.result.then(function (newItem) {
        $scope.rootItems.push(newItem);
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
                ItemDetails.update({'id':child.id, 'parent':parent});
            }
            if (child.order != i) {
                /* The ordering has changed: update the item */
                child.order = i;
                ItemDetails.update({'id':child.id, 'order':child.order});
            }
            /* Make a recursive call to check the children */
            updateOrder(child.children, child.id);
        }
    };
});


archtoolApp.controller("ModalItemEditor", function($scope, $modalInstance, Resource, Initial){
    $scope.item = new Resource(Initial);

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


