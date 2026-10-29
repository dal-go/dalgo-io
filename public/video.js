// Click-to-load film player. The page ships only a local poster and a button;
// nothing is requested from YouTube until the visitor presses play. Then the
// button is replaced by a youtube-nocookie.com iframe in the same 16:9 box.
(function () {
  "use strict";
  var boxes = document.querySelectorAll("[data-film]");
  Array.prototype.forEach.call(boxes, function (box) {
    var id = box.getAttribute("data-video-id");
    var button = box.querySelector(".film-play");
    if (!id || !button || !/^[A-Za-z0-9_-]{11}$/.test(id)) return;
    button.addEventListener("click", function () {
      var frame = document.createElement("iframe");
      frame.src = "https://www.youtube-nocookie.com/embed/" + encodeURIComponent(id) + "?autoplay=1&rel=0";
      frame.title = box.getAttribute("data-video-title") || "Video";
      frame.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
      frame.allowFullscreen = true;
      frame.referrerPolicy = "strict-origin-when-cross-origin";
      box.replaceChild(frame, button);
      frame.focus();
    }, { once: true });
  });
})();
