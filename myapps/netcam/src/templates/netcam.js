var lastrequest = null

netcam_success = function(result, status)
{
  var response = result['status'];
  var msg = lastrequest + ": ";

  if (response != 0) {
    msg += "Media server failed with status " + response;
    alert(msg);
  } else {
    msg += "Media server success";
  }
  
  console.log(msg);
}

netcam_error = function(xhr, status, error)
{
  var msg = lastrequest + ": Web server failed <"+status+":"+error+">";
  alert (msg);
  console.log(msg);
}

netcam_post = function(url, data)
{
  $.ajax({
    type: "POST",
    url: url,
    contentType: 'application/json;charset=UTF-8',
    data: JSON.stringify(data),
    dataType: "json",
    success: netcam_success,
    error: netcam_error
  });
}

netcam_play = function ()
{
  lastrequest = "Play";
  netcam_post("/play", {});

}

netcam_stop = function ()
{
  lastrequest = "Stop";
  netcam_post("/stop", {});

}

netcam_set_bitrate = function (bitrate)
{
  lastrequest = "SetBitrate";
  netcam_post("/set_bitrate", {'bitrate': bitrate});
}
