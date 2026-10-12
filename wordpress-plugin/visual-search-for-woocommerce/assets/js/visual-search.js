/**
 * Visual Search for WooCommerce — storefront widget.
 *
 * Flow: pick/take a photo -> POST /detect (items + boxes) -> tap an item ->
 * POST /search with its bounding box -> render product cards.
 * The first detected item is searched automatically so results appear without
 * an extra tap.
 */
(function () {
	'use strict';

	var cfg = window.vswConfig || {};
	var ALLOWED = ['image/jpeg', 'image/png', 'image/webp'];
	var el = {};
	var state = { uploadKey: null, items: [], size: [0, 0], active: -1, request: 0 };

	function $(sel, root) { return (root || document).querySelector(sel); }

	function api(path, body) {
		var headers = { 'X-WP-Nonce': cfg.nonce };
		var init = { method: 'POST', credentials: 'same-origin', headers: headers };
		if (body instanceof FormData) {
			init.body = body;
		} else {
			headers['Content-Type'] = 'application/json';
			init.body = JSON.stringify(body);
		}
		return fetch(cfg.restUrl + path, init).then(function (r) {
			return r.json().then(function (data) {
				if (!r.ok) { throw new Error((data && data.message) || cfg.i18n.error); }
				return data;
			});
		});
	}

	function show(step) {
		el.overlay.querySelectorAll('[data-vsw-step]').forEach(function (s) {
			s.hidden = s.getAttribute('data-vsw-step') !== step;
		});
	}

	function setStatus(text) { el.status.textContent = text || ''; }

	function open() {
		el.overlay.hidden = false;
		document.documentElement.classList.add('vsw-lock');
		el.close.focus();
	}

	function close() {
		el.overlay.hidden = true;
		document.documentElement.classList.remove('vsw-lock');
		reset();
	}

	function reset() {
		state = { uploadKey: null, items: [], size: [0, 0], active: -1, request: state.request + 1 };
		el.file.value = '';
		el.chips.textContent = '';
		el.boxes.textContent = '';
		el.results.textContent = '';
		if (el.preview.src && el.preview.src.indexOf('blob:') === 0) { URL.revokeObjectURL(el.preview.src); }
		el.preview.removeAttribute('src');
		setStatus('');
		show('pick');
	}

	function handleFile(file) {
		if (!file) { return; }
		if (ALLOWED.indexOf(file.type) === -1) { setStatus(cfg.i18n.badType); show('analyze'); return; }
		if (file.size > cfg.maxBytes) { setStatus(cfg.i18n.tooLarge); show('analyze'); return; }

		el.preview.src = URL.createObjectURL(file);
		show('analyze');
		setStatus(cfg.i18n.analyzing);

		var form = new FormData();
		form.append('image', file);
		var req = ++state.request;
		api('/detect', form).then(function (data) {
			if (req !== state.request) { return; }
			state.uploadKey = data.upload_key;
			state.items = data.items || [];
			state.size = data.image_size || [0, 0];
			renderChips();
			renderBoxes();
			if (state.items.length) { select(0); } else { setStatus(cfg.i18n.noResults); }
		}).catch(function (e) { if (req === state.request) { setStatus(e.message); } });
	}

	function itemLabel(item) {
		var rtl = document.documentElement.dir === 'rtl';
		return (item.icon ? item.icon + ' ' : '') + ((rtl && item.label_ar) ? item.label_ar : item.label);
	}

	function renderChips() {
		el.chips.textContent = '';
		state.items.forEach(function (item, i) {
			var b = document.createElement('button');
			b.type = 'button';
			b.className = 'vsw-chip';
			b.setAttribute('role', 'option');
			b.textContent = itemLabel(item);
			b.addEventListener('click', function () { select(i); });
			el.chips.appendChild(b);
		});
	}

	/** Boxes are positioned in % so they follow the responsive preview image. */
	function renderBoxes() {
		el.boxes.textContent = '';
		var w = state.size[0], h = state.size[1];
		if (!w || !h) { return; }
		state.items.forEach(function (item, i) {
			if (!item.bbox || item.bbox.length !== 4) { return; }
			var d = document.createElement('button');
			d.type = 'button';
			d.className = 'vsw-box';
			d.setAttribute('aria-label', itemLabel(item));
			d.style.left = (item.bbox[0] / w * 100) + '%';
			d.style.top = (item.bbox[1] / h * 100) + '%';
			d.style.width = ((item.bbox[2] - item.bbox[0]) / w * 100) + '%';
			d.style.height = ((item.bbox[3] - item.bbox[1]) / h * 100) + '%';
			d.addEventListener('click', function () { select(i); });
			el.boxes.appendChild(d);
		});
	}

	function select(i) {
		state.active = i;
		[el.chips, el.boxes].forEach(function (root) {
			Array.prototype.forEach.call(root.children, function (c, j) {
				c.classList.toggle('is-active', j === i);
				c.setAttribute('aria-selected', j === i ? 'true' : 'false');
			});
		});
		var item = state.items[i];
		setStatus(cfg.i18n.searching);
		el.results.textContent = '';
		var req = ++state.request;
		api('/search', {
			upload_key: state.uploadKey,
			bbox: item.bbox && item.bbox.length === 4 ? item.bbox : undefined,
			domain: item.domain,
			label: item.label,
			label_ar: item.label_ar
		}).then(function (data) {
			if (req !== state.request) { return; }
			renderProducts(data.products || []);
		}).catch(function (e) { if (req === state.request) { setStatus(e.message); } });
	}

	function renderProducts(products) {
		setStatus(products.length ? '' : cfg.i18n.noResults);
		var ul = document.createElement('ul');
		ul.className = 'vsw-grid';
		products.forEach(function (p) {
			var li = document.createElement('li');
			li.className = 'vsw-card';
			var a = document.createElement('a');
			a.href = p.url;
			var img = document.createElement('img');
			img.src = p.image;
			img.alt = p.name;
			img.loading = 'lazy';
			var name = document.createElement('span');
			name.className = 'vsw-name';
			name.textContent = p.name;
			var price = document.createElement('span');
			price.className = 'vsw-price';
			price.innerHTML = p.price_html; // sanitised server-side with wp_kses_post()
			a.append(img, name, price);
			li.appendChild(a);
			ul.appendChild(li);
		});
		el.results.textContent = '';
		el.results.appendChild(ul);
	}

	function init() {
		el.overlay = $('[data-vsw-overlay]');
		if (!el.overlay) { return; }
		el.file = $('[data-vsw-file]', el.overlay);
		el.drop = $('[data-vsw-drop]', el.overlay);
		el.preview = $('[data-vsw-preview]', el.overlay);
		el.boxes = $('[data-vsw-boxes]', el.overlay);
		el.chips = $('[data-vsw-chips]', el.overlay);
		el.status = $('[data-vsw-status]', el.overlay);
		el.results = $('[data-vsw-results]', el.overlay);
		el.close = $('[data-vsw-close]', el.overlay);

		document.addEventListener('click', function (e) {
			if (e.target.closest('[data-vsw-open]')) { e.preventDefault(); open(); }
		});
		el.close.addEventListener('click', close);
		el.overlay.addEventListener('click', function (e) { if (e.target === el.overlay) { close(); } });
		document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !el.overlay.hidden) { close(); } });
		$('[data-vsw-reset]', el.overlay).addEventListener('click', reset);
		$('[data-vsw-camera]', el.overlay).addEventListener('click', function () {
			el.file.setAttribute('capture', 'environment');
			el.file.click();
			el.file.removeAttribute('capture');
		});
		el.file.addEventListener('change', function () { handleFile(el.file.files[0]); });
		['dragover', 'dragleave', 'drop'].forEach(function (type) {
			el.drop.addEventListener(type, function (e) {
				e.preventDefault();
				el.drop.classList.toggle('is-over', type === 'dragover');
				if (type === 'drop' && e.dataTransfer.files.length) { handleFile(e.dataTransfer.files[0]); }
			});
		});
	}

	if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', init); } else { init(); }
}());
