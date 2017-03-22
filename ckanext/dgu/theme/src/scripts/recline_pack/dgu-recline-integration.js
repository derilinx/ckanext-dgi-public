// Monkey-patch broken functionality in Recline.
// We aren't using maps, havent loaded Leaflet, so do not try to use it.
recline.View.Map.prototype._setupMap = function() {};

// Integration point between DGU and Recline. Based on code from CKAN, stripped to requirements.
CKAN.Dgu.resourcePreviewer = (function($,my) {
    my.$dialog = function() { return $('#ckanext-datapreview'); }

    // **Public: Creates a link to the embeddable page.
    //
    // For a given DataExplorer state, this function constructs and returns the
    // url to the embeddable view of the current dataexplorer state.
    my.makeEmbedLink = function(explorerState) {
        var state = explorerState.toJSON();
        state.state_version = 1;

        var queryString = '?';
        var items = [];
        $.each(state, function(key, value) {
            if (typeof(value) === 'object') {
                value = JSON.stringify(value);
            }
            items.push(key + '=' + escape(value));
        });
        queryString += items.join('&');
        return embedPath + queryString;
    };

    // **Public: Loads a data preview**
    //
    // Fetches the preview data object from the link provided and loads the
    // parsed data from the webstore displaying it in the most appropriate
    // manner.
    //
    // link - Preview button.
    //
    // Returns nothing.
    my.loadPreviewDialog = function(resourceData) {
        //my.$dialog().html('<h4>Loading ... <img src="//assets.okfn.org/images/icons/ajaxload-circle.gif" class="loading-spinner" /></h4>');

        function initializeDataExplorer(dataset) {
            var views = [
                {
                    id: 'grid',
                    label: 'Grid',
                    view: new recline.View.Grid({
                        model: dataset
                    })
                },
                {
                    id: 'graph',
                    label: 'Graph',
                    view: new recline.View.Graph({
                        model: dataset
                    })
                },
                {
                    id: 'map',
                    label: 'Map',
                    view: new recline.View.Map({
                        model: dataset
                    })
                }
            ];
            var dataExplorer = new recline.View.DataExplorer({
                el: my.$dialog(),
                model: dataset,
                views: views,
                config: {
                    readOnly: true
                }
            });

            // Upon failure of the datapreivew to load...
            // 1. Hide the controls
            // 2. Hide the space reserved for the preview itself.
            // 3. Disable the Embed button
            dataExplorer.model.bind('query:fail', function(error) {
                $('#ckanext-datapreview .data-view-container').hide();
                $('#ckanext-datapreview .header').hide();
                $('.preview-header .btn').hide();
            });

            // -----------------------------
            // Setup the Embed modal dialog.
            // -----------------------------

            // embedLink holds the url to the embeddable view of the current DataExplorer state.
            var embedLink = $('.embedLink');

            // embedIframeText contains the '<iframe>' construction, which sources
            // the above link.
            var embedIframeText = $('.embedIframeText');

            // iframeWidth and iframeHeight control the width and height parameters
            // used to construct the iframe, and are also used in the link.
            var iframeWidth = $('.iframe-width');
            var iframeHeight = $('.iframe-height');

            // Update the embedLink and embedIframeText to contain the updated link
            // and update width and height parameters.
            function updateLink() {
                var link = my.makeEmbedLink(dataExplorer.state);
                var width = iframeWidth.val();
                var height = iframeHeight.val();
                link += '&width='+width+'&height='+height;

                // Escape '"' characters in {{link}} in order not to prematurely close
                // the src attribute value.
                embedIframeText.val($.mustache('<iframe frameBorder="0" width="{{width}}" height="{{height}}" src="{{link}}"></iframe>',
                                               {
                                                   link: link.replace(/"/g, '&quot;'),
                                                   width: width,
                                                   height: height
                                               }));
                embedLink.attr('href', link);
            }

            // Bind changes to the DataExplorer, or the two width and height inputs
            // to re-calculate the url.
            dataExplorer.state.bind('change', updateLink);
            for (var i=0; i<dataExplorer.pageViews.length; i++) {
                dataExplorer.pageViews[i].view.state.bind('change', updateLink);
            }

            iframeWidth.change(updateLink);
            iframeHeight.change(updateLink);

            // Initial population of embedLink and embedIframeText
            updateLink();

            // Finally, since we have a DataExplorer, we can show the embed button.
            $('.preview-header .btn').show();

            // will have to refactor if this can get called multiple times
            Backbone.history.start();
        }

        // 4 situations
        // a) have a webstore_url
        // b) csv or xls (but not webstore)
        // c) can be treated as plain text
        // d) none of the above but worth iframing (assumption is
        // that if we got here (i.e. preview shown) worth doing
        // something ...)
        resourceData.formatNormalized = my.normalizeFormat(resourceData.format);
        resourceData.url  = my.normalizeUrl(resourceData.url);
        var tmp = resourceData.url.split('/');
        tmp = tmp[tmp.length - 1];
        tmp = tmp.split('?'); // query strings
        tmp = tmp[0];
        var ext = tmp.split('.');

        if (resourceData.formatNormalized == '') {
            if (ext.length > 1) {
                resourceData.formatNormalized = ext[ext.length-1];
            }
        }

        if (resourceData.webstore_url) {
            resourceData.elasticsearch_url = '/api/data/' + resourceData.id;
            var dataset = new recline.Model.Dataset(resourceData, 'elasticsearch');
            initializeDataExplorer(dataset);
        }
        else if (resourceData.formatNormalized in {'csv': '', 'tsv': ''}) {
            if (ext.length > 1) {
                if (!(ext[ext.length-1] in {'csv': '', 'tsv': ''})) {
                    $(".dataset-resource-preview h2").addClass("hidden");
                    return
                }
            }
            // set format as this is used by Recline in setting format for DataProxy
            resourceData.format = resourceData.formatNormalized;
            var dataset = new recline.Model.Dataset(resourceData, 'dataproxy');
            initializeDataExplorer(dataset);
            $('.recline-query-editor .text-query').hide();
            google.charts.load('current', {packages: ['corechart']});
            // setTimeout(drawGraph, 4000)

            function drawGraph() {
                $('#ckanext-datapreview-extra').html()

                var d = [];
                $('#ckanext-datapreview table :not(tfoot) tr').each(function (i, e) {
                    d[i] = [];
                    $(this).children('th,td').children('.column-header-name,.data-table-cell-content').each(function(ii, vv){
                        var t = $(this).text().replace(/\,/g, '');
                        if (isNaN(+(t))) { d[i][ii] = $(this).text(); } else {d[i][ii] = +(t)}
                    });
                });
                d[0].shift()
                for (var n in d[0]) {d[0][n] = d[0][n].toString()}
                $('#ckanext-datapreview-extra').attr('style', 'height: 300px');
                var wrapper = new google.visualization.ChartWrapper({
                    chartType: 'LineChart',
                    containerId: 'ckanext-datapreview-extra',
                    dataTable: google.visualization.arrayToDataTable(d),
                    options: {legend: 'bottom'}
                });
                wrapper.draw();
            }
        }
        else if (resourceData.formatNormalized in {
            'n3': '',
            'n-triples': '',
            'turtle': '',
            'plain': '',
            'txt': ''
        }) {
            var _url = '/data/preview/' + resourceData.id + '?type=plain';
            my.getResourceDataDirect(_url, function(data) {
                my.showPlainTextData(data);
            });
        }
        else if (resourceData.formatNormalized in {'html':'', 'htm':''}
                 ||  resourceData.url.substring(0,23)=='http://docs.google.com/') {
            // we displays a fullscreen dialog with the url in an iframe.
            my.$dialog().empty();
            var el = $('<iframe></iframe>');
            el.attr('src', resourceData.url);
            el.attr('width', '100%');
            el.attr('height', '100%');
            // Change this to be a specific element for #977
            $('#ckanext-html-preview').append(el);
            my.$dialog().append(el);
        }
        else if (resourceData.formatNormalized in {
            'pdf':'',
            'doc': '', 'docx': '',
            'ppt': '', 'pptx': '',
            'xls': '', 'xlsx': '',
            'png': '', 'jpg': '', 'jpeg': '', 'gif': '', 'tiff': ''
        }) {
            my.$dialog().empty();
            var el = $('<iframe />');
            var u = resourceData.url;
            el.attr('src', "https://docs.google.com/gview?url=" + resourceData.url + "&embedded=true");
            el.css('width', '100%');
            el.css('height', '600px');
            my.$dialog().append(el);
        }
        else if (resourceData.formatNormalized in {'json-stat':''}) {
            my.$dialog().empty();
            var _url = '/data/preview/' + resourceData.id + '?type=json';
            google.charts.load('current', {packages: ['corechart']});

            my.getResourceDataDirect(_url, function (data) {
                if(data.error) {
                    my.showError(data.error);
                    return;
                }
                var j = JSONstat(data.data)

                var getUrlParameter = function getUrlParameter(sParam) {
                    var sPageURL = decodeURIComponent(window.location.hash.substring(1)), sURLVariables = sPageURL.split('&'), sParameterName, i;

                    for (i = 0; i < sURLVariables.length; i++) {
                        sParameterName = sURLVariables[i].split('=');

                        if (sParameterName[0] === sParam) { return sParameterName[1] === undefined ? true : sParameterName[1]; }
                    }
                    return undefined;
                }
                function insertParam(key, value) {
                    key = encodeURI(key); value = encodeURI(value);

                    var kvp = document.location.hash.substr(1).split('&');

                    var i=kvp.length; var x; while(i--) {
                        x = kvp[i].split('=');

                        if (x[0]==key) {
                            x[1] = value;
                            kvp[i] = x.join('=');
                            break;
                        }
                    }

                    if(i<0) {kvp[kvp.length] = [key,value].join('=');}

                    document.location.hash = '#' +kvp.join('&');
                }

                function drawGraph() {
                    $('#tbrowser-chart').html();

                    var d = [];
                    $('#ckanext-datapreview table :not(tfoot) tr').each(function (i, e) {
                        d[i] = [];
                        $(this).children('th,td').each(function(ii, vv){
                            var t = $(this).text().replace(/\,/g, '');
                            if (t === 'n/a') {
                                t = 0;
                            }

                            // is it a date?
                            var isDate = false;
                            // if we're a td, be permissive
                            if ($(this).prop('nodeName') === 'TH') {
                                if ((t.match(/^\d{4}$/) && (t.match(/^20/) || t.match(/^19/))) || t.match(/^\d{4}M\d{2}/) || t.match(/^\d{4}Q\d{2}/)) {
                                    t = new Date(t.replace('M', '-').replace('Q1', '-01').replace('Q2', '-04').replace('Q3', '-07').replace('Q4', '-10'));
                                    isDate = true;
                                }
                            } else {
                                if (t.match(/^\d{4}M\d{2}/) || t.match(/^\d{4}Q\d{2}/)) {
                                    t = new Date(t.replace('M', '-').replace('Q1', '-01').replace('Q2', '-04').replace('Q3', '-07').replace('Q4', '-10'));
                                    isDate = true;
                                }
                            }

                            if (isDate) {
                                d[i][ii] = t;
                            } else if (isNaN(+(t))) {
                                d[i][ii] = $(this).text();
                            } else {
                                d[i][ii] = +(t)
                            }
                        });
                    });
                    if (!isNaN(+new Date(d[1][0])) || !isNaN(parseInt(d[1][0]))) {
                        var wrapper = new google.visualization.ChartWrapper({
                            chartType: 'LineChart',
                            containerId: 'tbrowser-chart',
                            dataTable: google.visualization.arrayToDataTable(d),
                            options: {
                                legend: 'bottom',
                                animation: {
                                    startup: true,
                                    duration: 440,
                                    easing: 'inAndOut'
                                },
                                vAxis: {
                                    format: 'short'
                                }
                            }
                        });
                    } else {
                        var wrapper = new google.visualization.ChartWrapper({
                            chartType: 'ColumnChart',
                            containerId: 'tbrowser-chart',
                            dataTable: google.visualization.arrayToDataTable(d),
                            options: {
                                legend: 'bottom',
                                animation: {
                                    startup: true,
                                    duration: 440,
                                    easing: 'inAndOut'
                                }
                            }
                        });
                    }
                    wrapper.draw();
                }

                var r = getUrlParameter('r');
                var c = getUrlParameter('c');
                var preset = {};
                if (r && c) {
                    preset = {rows: r, cols: c};
                } else {
                    preset = {type: 'smaller'};
                }

                JSONstatUtils.tbrowser(j, my.$dialog()[0], {
                    tblclass: 'tbrowser',
                    preset: preset,
                    onload: google.charts.setOnLoadCallback(function () {setTimeout(drawGraph, 300)}),
                    onchange: function () {
                        insertParam('r', $('select[name=rows]').val())
                        insertParam('c', $('select[name=cols]').val())

                        google.charts.setOnLoadCallback(drawGraph);
                    }
                });
            });
        }
        else if (resourceData.formatNormalized in {'kml':''}) {
            my.$dialog().empty();
            my.$dialog().append('<div id="prevmap" style="height: 560px;width:100%"></div>');
            var map = L.map('prevmap').setView([53.505, -10.09], 7);
            L.tileLayer('https://stamen-tiles-{s}.a.ssl.fastly.net/terrain/{z}/{x}/{y}.jpg', {
              attribution: 'Map tiles by <a href="http://stamen.com">Stamen Design</a>, under <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a>. Data by <a href="http://openstreetmap.org">OpenStreetMap</a>, under <a href="http://creativecommons.org/licenses/by-sa/3.0">CC BY SA</a>.'

            }).addTo(map);
            var _url = '/data/preview/' + resourceData.id + '?type=plain';
            my.getResourceDataDirect(_url, function (data) {
                if(data.error) {
                    my.showError(data.error);
                    return;
                }
                var klayer = omnivore.kml.parse((new DOMParser()).parseFromString(data.data[0], 'text/xml'));
                klayer.eachLayer(function (layer) {
                    var p = layer.feature.properties;
                    var c = "<table class='table table-responsive'>"
                    for (var i in p) {
                        if (p[i]) {
                            if (p[i].toString().search('http') != -1) {p[i] = "<a href='" + p[i] + "'>" + p[i] + "</a>"; }
                            c += '<tr><th>' + i + '</th><td>' + p[i] + '</td>';
                        }
                    }
                    c+='</table>'
                    if (p.length != 0) {
                        layer.bindPopup(c);
                    }
                });
                map.fitBounds(klayer.getBounds().pad(0.1));
                klayer.addTo(map);
            });
        }
        else if (resourceData.formatNormalized in {'geojson':''}) {
            my.$dialog().empty();
            my.$dialog().append('<div id="prevmap" style="height: 560px;width:100%"></div>');
            var map = L.map('prevmap').setView([53.505, -10.09], 7);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(map);
            var _url = '/data/preview/' + resourceData.id + '?type=json';
            my.getResourceDataDirect(_url, function (data) {
                if(data.error) {
                    my.showError(data.error);
                    return;
                }
                proj4.defs("EPSG:2157", "+proj=tmerc +lat_0=53.5 +lon_0=-8 +k=0.99982 +x_0=600000 +y_0=750000 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=m +no_defs");
                if (data.data.crs && data.data.crs.type === 'none' && data.data.features[0].geometry.coordinates[0] > 10000) {
                    //assume ITM
                    data.data.crs = {
                        type: 'name',
                        properties: {name: 'urn:ogc:def:crs:EPSG::2157'}
                    }
                }
                var glayer = L.Proj.geoJson(data.data, {
                    onEachFeature: function (feature, layer) {
                        var p = feature.properties;
                        var c = "<table class='table table-responsive'>"
                        for (var i in p) {
                            if (p[i]) {
                                if (p[i].toString().search('http') != -1) {
                                    p[i] = "<a href='" + p[i] + "'>" + p[i] + "</a>";
                                }
                                c += '<tr><th>' + i + '</th><td>' + p[i] + '</td>';
                            }
                        }
                        c+='</table>'
                        if (p.length != 0) {
                            layer.bindPopup(c);
                        }
                    }
                });
                map.fitBounds(glayer.getBounds().pad(0.1));
                glayer.addTo(map);
            });
        }
        else if (resourceData.formatNormalized in {'json':''}) {
            my.$dialog().empty();
            my.$dialog().append('<div id="prevmap" style="height: 560px;width:100%"></div>');
            var map = L.map('prevmap').setView([53.505, -10.09], 7);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(map);
            var _url = '/data/preview/' + resourceData.id + '?type=json';
_url = "http://atlas.marine.ie/arcgis/rest/services/Fisheries/MapServer/23/query?where=1%3D1&text=&objectIds=&time=&geometry=&geometryType=esriGeometryEnvelope&inSR=&spatialRel=esriSpatialRelIntersects&relationParam=&outFields=&returnGeometry=true&maxAllowableOffset=&geometryPrecision=&outSR=&returnIdsOnly=false&returnCountOnly=false&orderByFields=&groupByFieldsForStatistics=&outStatistics=&returnZ=false&returnM=false&gdbVersion=&returnDistinctValues=false&returnTrueCurves=false&resultOffset=&resultRecordCount=&f=pjson";
            my.getResourceDataDirect(_url, function (data) {
                console.log(data);
                console.log(esri2geo.toGeoJSON(data.data));
            });
        }
        else {
            // Cannot reliably preview this item - with no mimetype/format information,
            // can't guarantee it's not a remote binary file such as an executable.
            // we really don't need this error though, it's not useful at all.
            //my.showError({
            //    title: 'Preview not available for data type: ' + resourceData.formatNormalized,
            //    message: ''
            //});
        }
    };

    // Public: Requests the formatted resource data from the webstore and
    // passes the data into the callback provided.
    //
    // preview - A preview object containing resource metadata.
    // callback - A Function to call with the data when loaded.
    //
    // Returns nothing.
    my.getResourceDataDirect = function(url, callback) {
        // $.ajax() does not call the "error" callback for JSONP requests so we
        // set a timeout to provide the callback with an error after x seconds.
        var timeout = 30000;
        var timer = setTimeout(function error() {
            callback({
                error: {
                    title: 'Request Error',
                    message: 'Dataproxy server did not respond after ' + (timeout / 1000) + ' seconds'
                }
            });
        }, timeout);

        // We need to provide the `cache: true` parameter to prevent jQuery appending
        // a cache busting `={timestamp}` parameter to the query as the webstore
        // currently cannot handle custom parameters.
        $.ajax({
            url: url,
            cache: true,
            dataType: 'json',
            success: function(data) {
                clearTimeout(timer);
                callback(data);
            },
            error: function(err) {
                clearTimeout(timer);
                callback({
                    error: {
                        title: 'Request Error',
                        message: 'There was an error processing the request'
                    }
                });
            }
        });
    };

    // Public: Displays a String of data in a fullscreen dialog.
    //
    // data    - An object of parsed CSV data returned by the webstore.
    //
    // Returns nothing.
    my.showPlainTextData = function(data) {
        if(data.error) {
            my.showError(data.error);
        } else {
            var content = $('<pre></pre>');
            for (var i=0; i<data.data.length; i++) {
                var row = data.data[i].join(',') + '\n';
                content.append(my.escapeHTML(row));
            }
            my.$dialog().html(content);
        }
    };

    my.showError = function (error) {
        var _html = _.template(
            '<div class="panel panel-danger"><div class="panel-heading"><strong><%= title %></strong></div><div class="panel-body"><%= message %></div></div>',
            error
        );
        my.$dialog().html(_html);
    };

    my.normalizeFormat = function(format) {
        var out = format.toLowerCase();
        out = out.split('/');
        out = out[out.length-1];
        return out;
    };

    my.normalizeUrl = function(url) {
        if (url.indexOf('https') === 0) {
            return 'http' + url.slice(5);
        } else {
            return url;
        }
    }

    // Public: Escapes HTML entities to prevent broken layout and XSS attacks
    // when inserting user generated or external content.
    //
    // string - A String of HTML.
    //
    // Returns a String with HTML special characters converted to entities.
    my.escapeHTML = function (string) {
        return string.replace(/&(?!\w+;|#\d+;|#x[\da-f]+;)/gi, '&amp;')
            .replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#x27')
            .replace(/\//g,'&#x2F;');
    };

    return my;
})(jQuery, CKAN.Dgu.resourcePreviewer || {});

var esri2geo={};(function(){function toGeoJSON(data,cb){if(typeof data==='string'){if(cb){ajax(data,function(err,d){toGeoJSON(d,cb)});return}else{throw new TypeError('callback needed for url')}}
var outPut={"type":"FeatureCollection","features":[]};var fl=data.features.length;var i=0;while(fl>i){var ft=data.features[i];var outFT={"type":"Feature","properties":prop(ft.attributes)};if(ft.geometry.x){outFT.geometry=point(ft.geometry)}else if(ft.geometry.points){outFT.geometry=points(ft.geometry)}else if(ft.geometry.paths){outFT.geometry=line(ft.geometry)}else if(ft.geometry.rings){outFT.geometry=poly(ft.geometry)}
outPut.features.push(outFT);i++}
cb(null,outPut)}
function point(geometry){return{"type":"Point","coordinates":[geometry.x,geometry.y]}}
function points(geometry){if(geometry.points.length===1){return{"type":"Point","coordinates":geometry.points[0]}}else{return{"type":"MultiPoint","coordinates":geometry.points}}}
function line(geometry){if(geometry.paths.length===1){return{"type":"LineString","coordinates":geometry.paths[0]}}else{return{"type":"MultiLineString","coordinates":geometry.paths}}}
function poly(geometry){if(geometry.rings.length===1){return{"type":"Polygon","coordinates":geometry.rings}}else{return decodePolygon(geometry.rings)}}
function decodePolygon(a){var coords=[],type;var len=a.length;var i=0;var len2=coords.length-1;while(len>i){if(ringIsClockwise(a[i])){coords.push([a[i]]);len2++}else{coords[len2].push(a[i])}
i++}
if(coords.length===1){type="Polygon"}else{type="MultiPolygon"}
return{"type":type,"coordinates":(coords.length===1)?coords[0]:coords}}
function ringIsClockwise(ringToTest){var total=0,i=0,rLength=ringToTest.length,pt1=ringToTest[i],pt2;for(i;i<rLength-1;i++){pt2=ringToTest[i+1];total+=(pt2[0]-pt1[0])*(pt2[1]+pt1[1]);pt1=pt2}
return(total>=0)}
function prop(a){var p={};for(var k in a){if(a[k]){p[k]=a[k]}}
return p}
function ajax(url,cb){if(typeof module!=="undefined"){var request=require("request");request(url,{json:!0},function(e,r,b){cb(e,b)});return}
var response;var req=new XMLHttpRequest();req.onreadystatechange=function(){if(req.readyState===4&&req.status===200){cb(null,JSON.parse(req.responseText))}};req.open("GET",url);req.send()}
if(typeof module!=="undefined"){module.exports=toGeoJSON}else{esri2geo.toGeoJSON=toGeoJSON}}())
