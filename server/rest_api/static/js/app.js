'use strict';

/* Controllers */
var archtoolApp = angular.module("archtoolApp", ['ngResource', 'ui.bootstrap']);
archtoolApp.config(function($resourceProvider) {
  $resourceProvider.defaults.stripTrailingSlashes = false;
});

archtoolApp.controller("SvgEditor", function ($scope) {
  $scope.blocks = [
    {'Id':1,
     'x': 20,
     'y': 20,
     'name': "Design",
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
     'end':$scope.blocks[1]}
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


archtoolApp.controller('SystemCtrl', function ($scope, $resource, $modal) {
    var Systems = $resource('/api/systems/');

    $scope.systems = Systems.query();
    $scope.currentSystem = null;

    $scope.new = function() {

      var modalWindow = $modal.open({
        animation: false,
        template: '<div class="modal-header">'+
                  '<h3 class="modal-title">Model Details</h3>'+
                  '</div><form role="form"><div class="form-group>'+
                  '  <label for="name">Name</label>'+
                  '  <input type="text" class="form-control" id="name" ng-model="system.name">'+
                  '</div><div class="form-group>'+
                  '  <label for="description">Description</label>'+
                  '  <input type="textarea" class="form-control" id="description"  ng-model="system.description">'+
                  '</div><div class="modal-footer">'+
                  '  <button class="btn btn-primary" ng-click="ok()">OK</button>'+
                  '  <button class="btn btn-warning" ng-click="cancel()">Cancel</button>'+
                  '</div></form>',
        controller: "ModalSystemEditor",
        resolve:{'Resource':function(){return Systems;}}
      });

      modalWindow.result.then(function (newSystem) {
        $scope.systems.push(newSystem);
        $scope.currentSystem = newSystem;
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

archtoolApp.controller("ItemsList", function($scope, $resource){
  /** How to access the currentSystem??? */
});