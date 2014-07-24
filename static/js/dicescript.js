var initialWinChance = 49.5;
var initialPayout = 2;
var _clientSeed = uuid.v4().replace(/-/g, "");

function BetViewModel() {
  var self = this;
  self._maxBetLimit = ko.observable(0);
  self.maxBetLimit = ko.computed(function() {
    return self._maxBetLimit();
  });
  self.betAmountEditing = ko.observable(false);
  self.payoutEditing = ko.observable(false);
  self.winChanceEditing = ko.observable(false);
  self.profit = ko.observable(0);
  self._betAmount = ko.observable(0);
  self.betAmount = ko.computed({
    read: function() {
      if (!self.betAmountEditing())
        return parseFloat(self._betAmount()).toFixed(8);
      return self.betAmount();
    },
    write: function(val) {
      if (parseFloat(val) > parseFloat(clientModel.clientBalance()))
          val = clientModel.clientBalance();
      var betAmt = parseFloat(val);
      var profit = (betAmt * self._payout()) - betAmt;
      if (profit > self._maxBetLimit()) {
        profit = self._maxBetLimit();
        betAmt = profit / ((self._payout()) - 1);
      }
      else if (profit < 0.00000001) {
        profit = 0;
      }
      self._betAmount(betAmt);
      self.profit(profit.toFixed(8));
      self._betAmount.valueHasMutated();
    }
  }).extend({notify: 'always'});
  self._payout = ko.observable(initialPayout);
  self.payout = ko.computed({
    read: function() {
      if (!self.payoutEditing())
        return parseFloat(self._payout()).toFixed(4);
      return self.payout();
    },
    write: function(val) {
      payout = parseFloat(val)
      if (payout > 100)
        payout = 100;
      else if (payout < 1.0001)
        payout = 1.0001;
      var betAmt = self._betAmount()
      var profit = ((betAmt * payout) - betAmt);
      if (profit > self._maxBetLimit()) {
        profit = self._maxBetLimit();
        betAmt = profit / ((self._payout()) - 1);
      }
      else if (profit < 0.00000001) {
        profit = 0;
      }
      self.betAmount(betAmt.toFixed(8));
      self.profit(profit.toFixed(8));
      self._payout(payout.toFixed(4));
      self._payout.valueHasMutated();
    }
  }).extend({notify: 'always'});
  self._winChance = ko.computed({
    read: function() {
      return ((100-houseEdge)/self._payout()).toFixed(2);
    },
    write: function(val) {
      var payout = (100-houseEdge)/val;
      var betAmt = self._betAmount()
      var profit = (betAmt * payout) - betAmt;
      if (profit > self._maxBetLimit()) {
        profit = self._maxBetLimit()
        betAmt = profit / ((self._payout()) - 1);
      }
      else if (profit < 0.00000001) {
        profit = 0;
      }
      self.betAmount(betAmt.toFixed(8));
      self.profit(profit.toFixed(8));
      self._payout(payout.toFixed(4));
    }
  });
  self.winChance = ko.computed({
    read: function() {
      if (!self.winChanceEditing())
        return parseFloat(self._winChance()).toFixed(2);
      return self.winChance();
    },
    write: function(val) {
      if (parseFloat(val) > 97.99)
        val = 97.99;
      else if (parseFloat(val) < 0.98)
        val = 0.98;
      self._winChance(val);
      //self._winChance.valueHasMutated();
    }
  }).extend({notify: 'always'});
  self.underAmount = ko.computed(function() {
    return ((100-houseEdge)/self._payout()).toFixed(2);
  });
  self.overAmount = ko.computed(function() {
    return (100-self.underAmount()).toFixed(2);
  });
  self.underText = ko.computed(function() {
    return "Roll Under " + self.underAmount();
  });
  self.overText = ko.computed(function() {
    return "Roll Over " + self.overAmount();
  });
  
  minBetAmount = function() {
    self.betAmount(0.00000001);
  }
  
  maxBetAmount = function() {
    try {
      self.betAmount(clientModel.clientBalance());
    }
    catch(err) {
      self.betAmount(0);
    }
  }

  doubleBetAmount = function() {
    var previousBetAmount = self.betAmount();
    var newAmount = previousBetAmount * 2;
    
    try {
      if (newAmount > clientModel.clientBalance())
        self.betAmount(clientModel.clientBalance())
      else
        self.betAmount(newAmount);
    }
    catch(err) {
        self.betAmount(0)
    }
    
  }

  halfBetAmount = function() {
    var previousBetAmount = self.betAmount();
    self.betAmount((previousBetAmount / 2));
  }
};

betViewModel = new BetViewModel();
ko.applyBindings(betViewModel, document.getElementById("betForm"));

$(document).ready(function() {      
  $("#loginForm").submit(function(e) {
    args = { username: JSON.stringify($('#loginusername').val()), password: JSON.stringify($('#loginpassword').val()) };
    args._xsrf = getCookie("_xsrf");
    $.ajax({
          url: '/login',
          type: "post",              
          data: args,
          success: function(res){
              window.location.reload();
          },
          error: function(jqxhr) {
            $("#invalidLogin").text(jqxhr.statusText);
            $("#invalidLogin").fadeIn();
          }
    });
    e.preventDefault();
  });

  $("#signupForm").submit(function(e) {
    args = { username: JSON.stringify($('#signupusername').val()), password: JSON.stringify($('#signuppassword').val()), email: JSON.stringify($('#signupemail').val()) };
    args._xsrf = getCookie("_xsrf");
    $.ajax({
          url: '/signup',
          type: "post",              
          data: args,
          success: function(res) {
            $("#signupStatus").text("Account successfully created. Logging you in now.");
            $("#signupStatus").fadeIn();

            setTimeout(function() {
              window.location.reload();
            }, 1000);
          },
          error: function(jqxhr) {
            $("#signupStatus").text(jqxhr.statusText);
            $("#signupStatus").fadeIn();
          }
    });
    e.preventDefault();
  });

  $("#rollUnder").click(function(e) {
    e.preventDefault();
    $("#rollUnder").attr('disabled', true);
    $("#rollOver").attr('disabled', true);
    $("#gameType").val("under")
    $("#betForm").trigger("submit")
  });

  $("#rollOver").click(function(e) {
    e.preventDefault();
    $("#rollUnder").attr('disabled', true);
    $("#rollOver").attr('disabled', true);
    $("#gameType").val("over")
    $("#betForm").trigger("submit")
  });

  $("#betForm").submit(function(e) {
    args = { betAmount: JSON.stringify($('#betFormBetAmount').val()), winChance: JSON.stringify($('#betFormWinChance').val()), clientSeed: JSON.stringify(_clientSeed), gameType: JSON.stringify($("#gameType").val()) };
    args._xsrf = getCookie("_xsrf");
    $.ajax({
          url: '/roll',
          type: "post",              
          data: args,
          success: function(res) {
            $("#betResultStatus").fadeOut(400, function() {
              if (res.result == "win")
                $(this).removeClass("warning info").addClass("success");
              else
                $(this).removeClass("success info").addClass("info");
              clientModel.clientBalance(res.bal);
              $(this).text(res.message).fadeIn(400);
            });
          },
          error: function(jqxhr) {
            $("#betResultStatus").fadeOut(400, function() {
              $("#betResultStatus").removeClass("success info").addClass("warning");
              $(this).text(jqxhr.statusText).fadeIn(400);
            });
          },
          complete: function(msg) {
            $("#rollUnder").attr('disabled', false);
            $("#rollOver").attr('disabled', false);
          }
    });
    e.preventDefault();
  });
});

function BetStatsModel() {
  var self = this;
  self.totalWagered = ko.observable(0);
  self.totalBets = ko.observable(0);
}

var betStatsModel = new BetStatsModel();
ko.applyBindings(betStatsModel, document.getElementById("siteStats"))

function getCookie(name) {
  var c = document.cookie.match("\\b" + name + "=([^;]*)\\b");
  return c ? c[1] : undefined;
}

function requestServerVars(userName) {
  var sock = new SockJS('http://' + window.location.host + '/status');
  sock.onopen = function (evt) {
    if (userName != undefined)
        sock.send(userName);
  };
  sock.onmessage = function(evt) {
      data = $.parseJSON(evt.data);
      updateType = data['type'];
      if (updateType == "seed" && userName != undefined) {
        seedModel.serverSeedHash(data['serverSeedHash']);
      }
      else if (updateType == "stats") {
        betStatsModel.totalWagered(data['totalWagered']);
        betStatsModel.totalBets(data['totalBets']);
        betViewModel._maxBetLimit(parseFloat(data['maxBetLimit']));
 
        for (var i = data.betHistory.length - 1;  i >= 0; i--) {
            if (data.betHistory[i][8] == "win") {
                $("#betHistory > tbody").prepend("<tr><td>" + data.betHistory[i][0] + "</td><td>" + data.betHistory[i][1] + "</td><td>" 
                + data.betHistory[i][2] + "</td><td>" + data.betHistory[i][3].toFixed(8) + "</td><td>" + data.betHistory[i][4].toFixed(4) + "</td><td>" + data.betHistory[i][5] 
                + "</td><td><strong>" + data.betHistory[i][6] + "</strong></td><td class='profit'>+" + data.betHistory[i][7].toFixed(8) + "</td></tr>")
            }
            else {
                $("#betHistory > tbody").prepend("<tr><td>" + data.betHistory[i][0] + "</td><td>" + data.betHistory[i][1] + "</td><td>" 
                + data.betHistory[i][2] + "</td><td>" + data.betHistory[i][3].toFixed(8) + "</td><td>" + data.betHistory[i][4].toFixed(4) + "</td><td>" + data.betHistory[i][5] 
                + "</td><td><strong>" + data.betHistory[i][6] + "</strong></td><td class='loss'>" + data.betHistory[i][7].toFixed(8) + "</td></tr>")
            }
        }
        
        while ($("#betHistory > tbody > tr").length > 30) {
            $('#betHistory tr:last').remove();
        }
        
      }
      else if (updateType == "client" && userName != undefined) {
        clientModel.clientBalance($.parseJSON(evt.data)['clientBalance']);
        setTimeout(function() { sock.send(userName) }, 30000);
      }
  };
  sock.onerror = function (evt) { };
}