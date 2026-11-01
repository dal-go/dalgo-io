(function () {
  'use strict';
  var year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();
  document.querySelectorAll('[data-lang-link]').forEach(function (link) {
    link.addEventListener('click', function () {
      if (location.hash) link.href = link.getAttribute('href').split('#')[0] + location.hash;
    });
  });
  document.querySelectorAll('.tabs').forEach(function (group) {
    var buttons = Array.from(group.querySelectorAll('.tab-btn'));
    var panels = group.parentNode.querySelectorAll('.tab-panel');
    function activate(button, focus) {
        var target = button.getAttribute('aria-controls');
        buttons.forEach(function (other) {
          var active = other === button;
          other.classList.toggle('is-active', active);
          other.setAttribute('aria-selected', active ? 'true' : 'false');
          other.tabIndex = active ? 0 : -1;
        });
        panels.forEach(function (panel) { panel.classList.toggle('is-active', panel.id === target); });
        if (focus) button.focus();
    }
    buttons.forEach(function (button, index) {
      button.tabIndex = button.getAttribute('aria-selected') === 'true' ? 0 : -1;
      button.addEventListener('click', function () { activate(button, false); });
      button.addEventListener('keydown', function (event) {
        var next;
        if (event.key === 'ArrowRight') next = (index + 1) % buttons.length;
        else if (event.key === 'ArrowLeft') next = (index + buttons.length - 1) % buttons.length;
        else if (event.key === 'Home') next = 0;
        else if (event.key === 'End') next = buttons.length - 1;
        else return;
        event.preventDefault();
        activate(buttons[next], true);
      });
    });
  });
}());
