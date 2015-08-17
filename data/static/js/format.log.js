var format_log = function(string) {
    if (!string) {
        return "";
    } else if (startswith(string, ">>> ")) {
        return "<u>" + string.replace(">>> ", "") + "</u>";
    } else if (startswith(string, ">>>> ")) {
        return "<b>" + string.replace(">>>> ", "") + "</b>";
    } else if (startswith(string, ">>>>> ")) {
        return "<i>" + string.replace(">>>>> ", "") + "</i>";
    } else if (startswith(string, ">>>>>> ")) {
        return "<span class='verbose'>" + string.replace(">>>>>> ", "") + "</span>";
    } else if (startswith(string, "[success]")) {
        return "<span class='success'>" + string.replace("[success]", "") + "</span>";
    } else if (startswith(string, "[failure]")) {
        return "<span class='failure'>" + string.replace("[failure]", "") + "</span>";
    }
    return string
}
var startswith = function(string, start) {
    return string.lastIndexOf(start, 0) === 0
}
var reload = function(element) {
    var href = element.attr("href"),
        target = $(element.data("target"));

    $.get(href, { from: target.find("li").length || 0 }).success(function(data) {
        if(data.done !== null) {
            location.reload();
        } else {
            for (var i = 0; i < data.logs.length; i++) {
                target.append($("<li>" + format_log(data.logs[i]) + "</li>"));
            };
            setTimeout(function() { reload(element); }, 10000);
        }
    }).error(function() {
        location.reload();
    });
}