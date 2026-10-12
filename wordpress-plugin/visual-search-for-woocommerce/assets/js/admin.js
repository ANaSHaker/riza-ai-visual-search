/**
 * Settings page: index the whole catalogue in small AJAX batches.
 */
(function () {
	'use strict';

	var cfg = window.vswAdmin;
	var btn = document.getElementById('vsw-index-start');
	var out = document.getElementById('vsw-index-status');
	if (!cfg || !btn) { return; }

	function fmt(s) {
		var args = Array.prototype.slice.call(arguments, 1), i = 0;
		return s.replace(/%(\d\$)?d/g, function () { return args[i++]; });
	}

	btn.addEventListener('click', function () {
		var indexed = 0, failed = 0, processed = 0;
		btn.disabled = true;

		function next(offset) {
			var body = new URLSearchParams({ action: 'vsw_index_batch', nonce: cfg.nonce, offset: String(offset) });
			fetch(cfg.ajaxUrl, { method: 'POST', credentials: 'same-origin', body: body })
				.then(function (r) { return r.json(); })
				.then(function (res) {
					if (!res.success) { throw new Error(); }
					if (res.data.done) {
						out.textContent = fmt(cfg.i18n.done, indexed, failed);
						btn.disabled = false;
						return;
					}
					indexed += res.data.indexed;
					failed += res.data.failed;
					processed = res.data.next_offset;
					out.textContent = fmt(cfg.i18n.running, processed);
					next(res.data.next_offset);
				})
				.catch(function () {
					out.textContent = cfg.i18n.error;
					btn.disabled = false;
				});
		}
		next(0);
	});
}());
