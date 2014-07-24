function VerifyViewModel() {
  var self = this;

  self.serverSeed = ko.observable("");
  self.clientSeed = ko.observable("");
  self.rollNumber = ko.observable(0);
  self.serverSeedHash = ko.observable("");
  self.result = ko.observable("");
  
  verifyResult = function() {
    self.serverSeedHash(CryptoJS.SHA512(self.serverSeed())).toString(CryptoJS.enc.Hex);
    seed = CryptoJS.SHA512(String(self.serverSeed()) + String(self.clientSeed()) + String(self.rollNumber())).toString(CryptoJS.enc.Hex);
    subSeed = seed.slice(-8);
    subSeedInt = parseInt(subSeed, 16);
    var m = new MersenneTwister(subSeedInt);
    res = (m.genrand_real1() * 100).toFixed(2);
    self.result(res);
  }
};

ko.applyBindings(new VerifyViewModel(), document.getElementById("verifyForm"));