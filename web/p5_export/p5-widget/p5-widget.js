/******/ (function(modules) { // webpackBootstrap
/******/ 	// The module cache
/******/ 	var installedModules = {};
/******/
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/
/******/ 		// Check if module is in cache
/******/ 		if(installedModules[moduleId])
/******/ 			return installedModules[moduleId].exports;
/******/
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = installedModules[moduleId] = {
/******/ 			exports: {},
/******/ 			id: moduleId,
/******/ 			loaded: false
/******/ 		};
/******/
/******/ 		// Execute the module function
/******/ 		modules[moduleId].call(module.exports, module, module.exports, __webpack_require__);
/******/
/******/ 		// Flag the module as loaded
/******/ 		module.loaded = true;
/******/
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/
/******/
/******/ 	// expose the modules object (__webpack_modules__)
/******/ 	__webpack_require__.m = modules;
/******/
/******/ 	// expose the module cache
/******/ 	__webpack_require__.c = installedModules;
/******/
/******/ 	// __webpack_public_path__
/******/ 	__webpack_require__.p = "";
/******/
/******/ 	// Load entry module and return exports
/******/ 	return __webpack_require__(0);
/******/ })
/************************************************************************/
/******/ ([
/* 0 */
/***/ (function(module, exports, __webpack_require__) {

	"use strict";
	var defaults = __webpack_require__(1);
	var MY_FILENAME = 'p5-widget.js';
	var IFRAME_FILENAME = 'p5-widget.html';
	var IFRAME_STYLE = [
	    'width: 100%',
	    'background-color: white',
	    'border: 1px solid #ec245e',
	    'box-sizing: border-box'
	];
	var AVOID_MIXED_CONTENT_WARNINGS = true;
	var myScriptEl = getMyScriptEl();
	var myBaseURL = getMyBaseURL(myScriptEl.src);
	var autoload = !myScriptEl.hasAttribute('data-manual');
	var nextId = 1;
	function getMyBaseURL(url) {
	    var baseURL = url.slice(0, -MY_FILENAME.length);
	    if (AVOID_MIXED_CONTENT_WARNINGS) {
	        if (window.location.protocol === 'http:' && /^https:/.test(baseURL)) {
	            // Our script was loaded over HTTPS, but the embedding page is
	            // using HTTP. This is likely to result in mixed content warnings
	            // if e.g. the widget's sketch wants to load resources relative to
	            // the embedding page's URL, so let's just embed the widget over
	            // HTTP instead of HTTPS.
	            baseURL = baseURL.replace('https:', 'http:');
	        }
	    }
	    return baseURL;
	}
	function getMyScriptEl() {
	    return (document.currentScript ||
	        document.querySelectorAll("script[src$='" + MY_FILENAME + "']")[0]);
	}
	// http://stackoverflow.com/a/7557433/2422398
	function isElementInViewport(el) {
	    var rect = el.getBoundingClientRect();
	    return (rect.bottom >= 0 &&
	        rect.right >= 0 &&
	        rect.top <= (window.innerHeight ||
	            document.documentElement.clientHeight) &&
	        rect.left <= (window.innerWidth ||
	            document.documentElement.clientWidth));
	}
	function getDataHeight(el) {
	    var height = parseInt(el.getAttribute('data-height'));
	    if (isNaN(height))
	        height = defaults.HEIGHT;
	    return height;
	}
	function absoluteURL(url) {
	    var a = document.createElement('a');
	    a.setAttribute('href', url);
	    return a.href;
	}
	function getSketch(url, cb) {
	    var error = function (msg) {
	        var lines = ['// p5.js-widget failed to retrieve ' + url + '.'];
	        if (msg && typeof (msg) == 'string') {
	            lines.push('// ' + msg);
	        }
	        cb(lines.join('\n'));
	    };
	    var req = new XMLHttpRequest();
	    req.open('GET', url);
	    req.onload = function () {
	        if (req.status == 200) {
	            cb(req.responseText);
	        }
	        else {
	            error('Server returned HTTP ' + req.status + '.');
	        }
	    };
	    req.onerror = error;
	    req.send(null);
	}
	function replaceScriptWithWidget(el) {
	    var iframe = document.createElement('iframe');
	    var height = getDataHeight(el);
	    var previewWidth = parseInt(el.getAttribute('data-preview-width'));
	    var baseSketchURL = absoluteURL(el.getAttribute('data-base-url'));
	    var p5version = el.getAttribute('data-p5-version');
	    var maxRunTime = parseInt(el.getAttribute('data-max-run-time'));
	    var autoplay = el.hasAttribute('data-autoplay');
	    var url;
	    var qsArgs = [
	        'id=' + encodeURIComponent(el.getAttribute('data-id'))
	    ];
	    var style = IFRAME_STYLE.slice();
	    function makeWidget(sketch) {
	        qsArgs.push('sketch=' + encodeURIComponent(sketch));
	        style.push('min-height: ' + height + 'px');
	        url = myBaseURL + IFRAME_FILENAME + '?' + qsArgs.join('&');
	        iframe.setAttribute('src', url);
	        iframe.setAttribute('style', style.join('; '));
	        el.parentNode.replaceChild(iframe, el);
	    }
	    if (!isNaN(previewWidth) && previewWidth >= 0) {
	        qsArgs.push('previewWidth=' + previewWidth);
	    }
	    if (!isNaN(maxRunTime) && maxRunTime >= 0) {
	        qsArgs.push('maxRunTime=' + maxRunTime);
	    }
	    if (baseSketchURL) {
	        qsArgs.push('baseSketchURL=' + encodeURIComponent(baseSketchURL));
	    }
	    if (p5version) {
	        qsArgs.push('p5version=' + encodeURIComponent(p5version));
	    }
	    if (autoplay) {
	        qsArgs.push('autoplay=on');
	    }
	    if (el.src && el.textContent && el.textContent.trim()) {
	        return makeWidget([
	            '// Your widget includes both a "src" attribute and inline script',
	            '// content, which makes no sense. Please remove one of them.'
	        ].join('\n'));
	    }
	    if (el.src) {
	        getSketch(el.src, makeWidget);
	    }
	    else {
	        makeWidget(el.textContent);
	    }
	}
	function whenVisible(el, cb) {
	    var CHECK_INTERVAL_MS = 1000;
	    var interval;
	    function maybeMakeVisible() {
	        if (!isElementInViewport(el))
	            return;
	        clearInterval(interval);
	        window.removeEventListener('scroll', maybeMakeVisible, false);
	        window.removeEventListener('resize', maybeMakeVisible, false);
	        cb(el);
	    }
	    // We want to check at a fixed interval as a fallback, to make
	    // sure that we detect when the element is visible even outside
	    // of the usual means (e.g., because the user did some
	    // sort of pinch/zoom gesture).
	    interval = setInterval(maybeMakeVisible, 1000);
	    window.addEventListener('scroll', maybeMakeVisible, false);
	    window.addEventListener('resize', maybeMakeVisible, false);
	    maybeMakeVisible();
	}
	function lazilyReplaceScriptWithWidget(el) {
	    var height = getDataHeight(el);
	    el.style.display = 'block';
	    el.style.fontSize = '0';
	    el.style.width = '100%';
	    el.style.minHeight = height + 'px';
	    el.style.background = '#f0f0f0';
	    if (!el.hasAttribute('data-id')) {
	        el.setAttribute('data-id', nextId.toString());
	        nextId++;
	    }
	    whenVisible(el, replaceScriptWithWidget);
	}
	function lazilyReplaceAllScriptsWithWidget() {
	    var scripts = document.querySelectorAll("script[type='text/p5']");
	    [].slice.call(scripts).forEach(function (el) {
	        lazilyReplaceScriptWithWidget(el);
	    });
	}
	if (autoload) {
	    if (document.readyState === 'complete') {
	        lazilyReplaceAllScriptsWithWidget();
	    }
	    else {
	        window.addEventListener('load', lazilyReplaceAllScriptsWithWidget, false);
	    }
	}
	window['p5Widget'] = {
	    baseURL: myBaseURL,
	    url: myBaseURL + MY_FILENAME,
	    replaceScript: lazilyReplaceScriptWithWidget,
	    replaceAll: lazilyReplaceAllScriptsWithWidget,
	    defaults: defaults
	};


/***/ }),
/* 1 */
/***/ (function(module, exports) {

	"use strict";
	exports.P5_VERSION = '0.4.23';
	exports.PREVIEW_WIDTH = 150;
	exports.HEIGHT = 300;
	exports.MAX_RUN_TIME = 1000;


/***/ })
/******/ ]);
//# sourceMappingURL=p5-widget.js.map