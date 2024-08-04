// http://stackoverflow.com/a/1173319/2422398
function selectText(containerid) {
  if (document.selection) {
    var range = document.body.createTextRange();
    range.moveToElementText(document.getElementById(containerid));
    range.select();
  } else if (window.getSelection) {
    var range = document.createRange();
    range.selectNode(document.getElementById(containerid));
    window.getSelection().addRange(range);
  }
}

function scrollHashTargetIntoView() {
  var el = document.getElementById(window.location.hash.slice(1));

  if (el) el.scrollIntoView();
}

$(function() {
  var FORCE_HTTPS = false;
  var FORCE_PROTOCOL_RELATIVE = true;
  var widgetURL = p5Widget.url;
  var simplifyHtml = function(html) {
    // This will convert e.g. data-autoplay="", which is how browsers
    // will always serialize the HTML, to just data-autoplay, which
    // reads better.
    return html.replace(/=""/g, '');
  };

  if (FORCE_HTTPS) {
    widgetURL = widgetURL.replace('http:', 'https:');
  } else if (FORCE_PROTOCOL_RELATIVE) {
    widgetURL = widgetURL.replace(/^https?:/, '');
  }

  $("#script-tag-example").text('<script src="' + widgetURL + '"></script>');

  $("[data-insert-default]").each(function() {
    var name = this.getAttribute('data-insert-default');

    if (name in p5Widget.defaults) {
      $(this).text(p5Widget.defaults[name]);
    } else {
      console.log("p5Widget.defaults." + name + " does not exist!");
    }
  });

  $('script[type="text/p5"]').each(function() {
    if (this.hasAttribute('data-hide-sourcecode')) return;

    var div = $('<div></div>');
    var code = $('<code class="language-markup"></code>');

    $(this).clone().appendTo(div);

    code.text(simplifyHtml(div.html()));

    $(this).before(code);

    code.wrap('<pre></pre>');
  });

  Prism.highlightAll();
  p5Widget.replaceAll();

  $("#script-tag-example").click(function() {
    selectText(this.id);
  });

  // Most browsers automatically do this for us, but Firefox doesn't,
  // so force it ourselves:
  //
  // https://github.com/toolness/p5.js-widget/issues/50
  scrollHashTargetIntoView();
});
