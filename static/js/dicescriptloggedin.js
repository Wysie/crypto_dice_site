function SeedsModel() {
  var self = this;
  self.serverSeedHash = ko.observable("");
  self.clientSeed = ko.computed({
    read: function() {
      return _clientSeed;
    },
    write: function(val) {
      _clientSeed = val;
    }
  }).extend({notify: 'always'});
};

function ClientModel() {
  var self = this;
  self.clientBalance = ko.observable(0);
  self.withdrawAmountEditing = ko.observable(false);  
  self._withdrawAmount = ko.observable(0);
  self.withdrawAmount = ko.computed({
    read: function() {
      if (!self.withdrawAmountEditing())
        return parseFloat(self._withdrawAmount()).toFixed(8);
      return self.withdrawAmount();
    },
    write: function(val) {
      if (parseFloat(val) > parseFloat(self.clientBalance()))
        val = self.clientBalance()
      self._withdrawAmount(val);
      self._withdrawAmount.valueHasMutated();
    }
  }).extend({notify: 'always'});
  
  balanceWithdraw = function() {
    self.withdrawAmount(self.clientBalance());
  }
}

var seedModel = new SeedsModel();
var clientModel = new ClientModel();
ko.applyBindings(seedModel, document.getElementById("seedsModal"))
ko.applyBindings(clientModel, document.getElementById("accountInfo"))

$(document).ready(function() {
  $("#generateClientSeed").click(function(e) {
    e.preventDefault();
    _clientSeed = uuid.v4().replace(/-/g, "");
    $("#clientSeed").val(_clientSeed)
  });
  
  $("#withdrawForm").submit(function(e) {
    args = { withdrawAddress: JSON.stringify($('#withdrawAddress').val()), withdrawAmount: JSON.stringify($('#withdrawAmount').val()) };
    args._xsrf = getCookie("_xsrf");
    $.ajax({
          url: '/withdraw',
          type: "post",              
          data: args,
          success: function(res){
            clientModel.clientBalance(res.bal);
            $("#withdrawStatus").text("Withdraw request sent.");
            $("#withdrawStatus").fadeIn();
          },
          error: function(jqxhr) {
            $("#withdrawStatus").text(jqxhr.statusText);
            $("#withdrawStatus").fadeIn();
          }
    });
    e.preventDefault();
  });
});