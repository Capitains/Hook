var re = /(>>>>>>[^>]+)/gm;

var format_log = function(string) {
    if (!string) {
        return "";
    } else if (startswith(string, ">>> ")) {
        return "<u>" + string.replace(">>> ", "") + "</u>";
    } else if (startswith(string, ">>>> ")) {
        return "<b>" + string.replace(">>>> ", "") + "</b>";
    } else if (startswith(string, ">>>>> ")) {
        return "<i>" + string.replace(">>>>> ", "") + "</i>";
    } else if (startswith(string, "[success]")) {
        return "<span class='success'>" + string.replace("[success]", "") + "</span>";
    } else if (startswith(string, "[failure]")) {
        return "<span class='failure'>" + string.replace("[failure]", "") + "</span>";
    } else {
        var string2 = []
        while ((m = re.exec(string)) !== null) {
            string2.push("<span class='verbose'>" + m[0].replace(">>>>>> ", "") + "</span>");
            if (m.index === re.lastIndex) {
                re.lastIndex++;
            }
        }
        if (string2.length === 1) {
            return string2[0];
        } else if (string2.length > 1) {
            return string2.join("</li><li>");
        }
    }
    return string
}
var logs = function(target, url) {
    var child = target.children();
    if(child.length == 0) {
        $.get(url, function(data) {
            var ol = $("<ol />", {"class": "logs"}),
                li = function(data) {
                var li = $("<li />");
                li.html(format_log(data));
                return li;
            };

            for ( var i = 0, l = data.logs.length; i < l; i++ ) {
                ol.append(li(data.logs[i]));
            }
            target.append(ol);
        });
    } else {
        target.toggle();
    }
}
var startswith = function(string, start) {
    return string.lastIndexOf(start, 0) === 0
}
var reload = function(element) {
    var href = element.attr("href"),
        target = $(element.data("target"));

    $.get(href, { start: target.find("li").length || 0 }).success(function(data) {
        for (var i = 0; i < data.logs.length; i++) {
            target.append($("<li>" + format_log(data.logs[i]) + "</li>"));
        };
        if ((data.status_string != "failed" && data.status_string != "error" && data.status_string != "success") || (data.logs_count !== data.end + 1)) {
            setTimeout(function() { reload(element); }, 10000);
        }
    }).error(function() {
        location.reload();
    });
}