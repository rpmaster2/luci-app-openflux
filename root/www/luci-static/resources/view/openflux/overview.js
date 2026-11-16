'use strict';
'require view';
'require form';
'require uci';
'require fs';
'require ui';

return view.extend({
	load: function() {
		return Promise.all([
			uci.load('openflux'),
			fs.exec('/etc/init.d/openflux', [ 'status' ]).catch(function() {
				return { code: -1, stdout: '' };
			}),
			fs.exec('/sbin/logread', [ '-e', 'openflux' ]).catch(function() {
				return { stdout: '' };
			})
		]);
	},

	handleAction: function(action) {
		ui.showModal(null, [
			E('p', { class: 'spinning' }, _('Running %s…').format(action))
		]);

		return fs.exec('/etc/init.d/openflux', [ action ]).then(function() {
			window.location.reload();
		}).catch(function(err) {
			ui.hideModal();
			ui.addNotification(null, E('p', {}, _('Failed: %s').format(err.message || err)), 'danger');
		});
	},

	render: function(data) {
		var running = data[1] && (data[1].code === 0);
		var logtext = (data[2] && data[2].stdout) ? data[2].stdout.trim().split('\n').slice(-40).join('\n') : '';

		var activeId = uci.get('openflux', 'main', 'active') || '';
		var activeName = activeId ? (uci.get('openflux', activeId, 'name') || activeId) : _('none');

		var m = new form.Map('openflux', _('OpenFlux'),
			_('Emergency tunnel client. Profiles are stored here, but only one selected profile runs at a time and exposes a local SOCKS5 port. Proxy managers (Mihomo, sing-box, etc.) can use that port as a regular upstream proxy.'));

		var s = m.section(form.NamedSection, 'main', 'openflux', _('Service'));
		s.anonymous = true;

		var o = s.option(form.Flag, 'enabled', _('Enable service'),
			_('When disabled, nothing is started and no memory is used.'));
		o.default = '0';
		o.rmempty = false;

		o = s.option(form.ListValue, 'active', _('Active profile'),
			_('Only this profile is started. Add more profiles in the table below.'));
		uci.sections('openflux', 'profile').forEach(function(p) {
			o.value(p['.name'], p.name || p['.name']);
		});
		o.rmempty = false;

		o = s.option(form.Value, 'binary', _('Client binary'),
			_('Path to the OpenFlux client executable.'));
		o.default = '/usr/bin/openflux';
		o.rmempty = false;

		o = s.option(form.Value, 'archive', _('Compressed binary (optional)'),
			_('Path to a gzip-compressed client binary. If the executable above is missing, it is unpacked to /tmp/openflux on start — useful on routers with little flash.'));
		o.placeholder = '/root/openflux.gz';
		o.rmempty = true;

		var g = m.section(form.GridSection, 'profile', _('Profiles'),
			_('One profile = one SOCKS5 port. A new profile appears in the "Active profile" list after saving and reloading the page.'));
		g.addremove = true;
		g.anonymous = true;
		g.sortable = true;
		g.nodescriptions = false;

		o = g.option(form.Value, 'name', _('Name'));
		o.placeholder = 'Profile 1';
		o.rmempty = false;

		o = g.option(form.ListValue, 'transport', _('Transport'));
		o.value('telemost', 'Telemost');
		o.value('cupsonline', 'Cups.online');
		o.value('yandex', 'Yandex.Docs');
		o.value('vyandex', 'Yandex.Volga');
		o.value('mailru', 'Mail.ru');
		o.value('avito', 'Avito');
		o.value('oneme', 'MAX');
		o.value('direct', 'Direct');
		o.default = 'telemost';
		o.rmempty = false;

		o = g.option(form.Value, 'socks', _('SOCKS5'));
		o.placeholder = '127.0.0.1:1081';
		o.default = '127.0.0.1:1081';
		o.rmempty = false;
		o.description = _('Local port this profile listens on.');

		o = g.option(form.Value, 'url', _('Link / room'));
		o.placeholder = 'https://telemost.yandex.ru/j/...';
		o.rmempty = false;
		o.description = _('Conference link for Telemost, room string for Cups.online, etc.');

		o = g.option(form.Value, 'key', _('Encryption key'));
		o.placeholder = '64 hex characters';
		o.rmempty = true;
		o.password = false;
		o.description = _('Must match the exit node key. Stored in UCI, written to /tmp on start.');

		m.on_after_commit = function() {
			return fs.exec('/etc/init.d/openflux', [ 'restart' ]);
		};

		return m.render().then(function(node) {
			var self = this;

			var badge = E('span', {
				class: 'label ' + (running ? 'success' : 'danger'),
				style: 'margin-left:8px'
			}, running ? _('running') : _('stopped'));

			var activeBadge = E('span', {
				class: 'label',
				style: 'margin-left:8px'
			}, _('profile: %s').format(activeName));

			var btnRestart = E('button', {
				class: 'btn cbi-button cbi-button-action',
				click: ui.createHandlerFn(self, 'handleAction', 'restart')
			}, _('Restart'));

			var btnStop = E('button', {
				class: 'btn cbi-button cbi-button-reset',
				disabled: running ? null : 'disabled',
				click: ui.createHandlerFn(self, 'handleAction', 'stop')
			}, _('Stop'));

			var btnStart = E('button', {
				class: 'btn cbi-button cbi-button-apply',
				disabled: running ? 'disabled' : null,
				click: ui.createHandlerFn(self, 'handleAction', 'start')
			}, _('Start'));

			var statusBox = E('div', { class: 'cbi-section' }, [
				E('h3', {}, [ _('Service state'), badge, activeBadge ]),
				E('div', { class: 'cbi-section-actions' }, [ btnRestart, ' ', btnStart, ' ', btnStop ])
			]);

			var logBox = E('div', { class: 'cbi-section' }, [
				E('h3', {}, _('Recent log lines')),
				E('textarea', {
					readonly: 'readonly',
					rows: 14,
					style: 'width:100%;font-family:monospace;font-size:11px;white-space:pre'
				}, logtext || _('no data'))
			]);

			node.insertBefore(statusBox, node.firstChild);
			node.appendChild(logBox);

			return node;
		}.bind(this));
	}
});
