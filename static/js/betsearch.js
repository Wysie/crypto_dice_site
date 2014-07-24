$(document).ready(function() {
  $("#betSearchForm").submit(function(e) {
    args = { q: $('#q').val(), output: "json" };
    $.ajax({
          url: '/bets',
          type: "get",              
          data: args,
          success: function(res) {
            results = $.parseJSON(res).searchResults;
            $("#betSearchResults").fadeOut(400, function() {
              processResults(results);
              $(this).fadeIn(400);
            });
          },
          error: function(jqxhr) {
            alert(jqxhr);
          }
    });
    e.preventDefault();
  });
});

function processResults(results) {
    $('#betSearchResults > tbody').empty();
    for (var i = results.length - 1;  i >= 0; i--) {
        $("#betSearchResults > tbody").prepend("<tr><td>" + results[i]['bet_id'] + "</td><td>" + results[i]['username'] + "</td><td>" 
        + results[i]['bet_time'] + "</td><td>" + results[i]['bet_amount'].toFixed(8) + "</td><td>" + results[i]['payout'].toFixed(4) + "</td><td>" + results[i]['game'] 
        + "</td><td>" + results[i]['roll'] + "</td><td>" + results[i]['profit'].toFixed(8) + "</td><td>" + results[i]['result'] + "</td><td>" + results[i]['server_seed']
        + "</td><td>" + results[i]['client_seed'] + "</td></tr>")
    }
    $('#betSearchResults').dataTable({
        "aaSorting": [[ 0, "desc" ]],
        "bDestroy": true,
    });
        
    /*$('#betSearchResults').dataTable( {
        "sDom": 'T<"clear">lfrtip',
        "oTableTools": {
            "sSwfPath": "/swf/copy_csv_xls_pdf.swf"
        }
    } );*/
}