// Bootstrap data is injected as a non-executable JSON block (CSP-friendly:
// no inline <script> to whitelist). Falls back to {} if absent.
const HC = (() => {
  const el = document.getElementById('hybridcal-data');
  try { return el ? JSON.parse(el.textContent) : {}; }
  catch (e) { return {}; }
})();

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function plusMonthsISO(months) {
  const d = new Date();
  d.setMonth(d.getMonth() + months);
  return d.toISOString().slice(0, 10);
}

function eventFilter() {
  const defaultFrom = todayISO();
  const defaultTo = plusMonthsISO(9);
  return {
    events: [],
    formats: HC.formats || {},
    regions: HC.regions || [],
    lang: HC.lang || 'de',
    locale: HC.locale || 'de-DE',
    defaultRegions: HC.defaultRegions || ['dach'],
    defaultDateFrom: defaultFrom,
    defaultDateTo: defaultTo,
    basePath: HC.basePath || '',
    tbaLabel: HC.tbaLabel || 'TBA',
    filters: {
      formats: [],
      regions: [],
      dateFrom: defaultFrom,
      dateTo: defaultTo,
    },
    search: '',
    view: 'map',
    map: null,
    cluster: null,
    calendarYear: new Date().getFullYear(),
    calendarMonth: new Date().getMonth(),
    _initialized: false,

    async init() {
      this.filters.regions = [...this.defaultRegions];
      const response = await fetch(this.basePath + '/events.json');
      this.events = await response.json();
      this.loadFromURL();
      this._initialized = true;
      this.$watch('filters', () => {
        this.saveToURL();
        if (this.view === 'map' && this.map) this.renderMarkers();
      }, { deep: true });
      this.$watch('search', () => {
        this.saveToURL();
        if (this.view === 'map' && this.map) this.renderMarkers();
      });
      if (this.view === 'map') {
        this.$nextTick(() => {
          this.initMap();
          setTimeout(() => {
            this.map.invalidateSize();
            this.renderMarkers();
          }, 100);
        });
      }
    },

    regionsAreDefault() {
      const d = this.defaultRegions;
      return this.filters.regions.length === d.length &&
        this.filters.regions.every(r => d.includes(r));
    },

    get activeFilterCount() {
      let n = 0;
      if (this.filters.formats.length > 0) n++;
      if (!this.regionsAreDefault()) n++;
      if (this.search) n++;
      // date range is always visible in the UI — don't count it
      return n;
    },

    matches(e, overrides = {}) {
      const formats = overrides.formats ?? this.filters.formats;
      const regions = overrides.regions ?? this.filters.regions;
      const dateFrom = overrides.dateFrom ?? this.filters.dateFrom;
      const dateTo = overrides.dateTo ?? this.filters.dateTo;
      const search = (overrides.search ?? this.search).toLowerCase().trim();

      // TBA events (no date) are filtered out by the date range.
      if (!e.date_start || !e.date_end) return false;
      // Date-range overlap: event spans [date_start..date_end], filter is [from..to]
      if (dateFrom && e.date_end < dateFrom) return false;
      if (dateTo && e.date_start > dateTo) return false;

      if (formats.length > 0 && !formats.includes(e.format)) return false;
      if (regions.length > 0 && !regions.includes(e.region)) return false;
      if (search) {
        const formatName = this.formats[e.format]?.name || '';
        const haystack = [
          e.name,
          e.location.city,
          e.location.venue || '',
          formatName,
        ].join(' ').toLowerCase();
        if (!haystack.includes(search)) return false;
      }
      return true;
    },

    get filtered() {
      return this.events.filter(e => this.matches(e));
    },

    countForFormat(id) {
      return this.events.filter(
        e => e.format === id && this.matches(e, { formats: [] })
      ).length;
    },

    countForRegion(id) {
      return this.events.filter(
        e => e.region === id && this.matches(e, { regions: [] })
      ).length;
    },

    formatDate(iso) {
      if (!iso) return this.tbaLabel;
      const d = new Date(iso);
      return d.toLocaleDateString(this.locale, {
        weekday: 'short',
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      });
    },

    setView(v) {
      this.view = v;
      this.saveToURL();
      if (v === 'map') {
        this.$nextTick(() => {
          if (!this.map) this.initMap();
          else this.map.invalidateSize();
          this.renderMarkers();
        });
      }
    },

    // ── Calendar view ─────────────────────────────────────────────
    get weekdays() {
      // Jan 1, 2024 was a Monday → use it as anchor for Mo-So order
      return [...Array(7).keys()].map(i => {
        const d = new Date(Date.UTC(2024, 0, i + 1));
        return d.toLocaleDateString(this.locale, {
          weekday: 'short', timeZone: 'UTC',
        });
      });
    },

    get currentMonthLabel() {
      return new Date(this.calendarYear, this.calendarMonth, 1)
        .toLocaleDateString(this.locale, { month: 'long', year: 'numeric' });
    },

    get calendarDays() {
      const first = new Date(this.calendarYear, this.calendarMonth, 1);
      // getDay(): 0=Sun..6=Sat ; we want 0=Mon..6=Sun
      const firstWeekday = (first.getDay() + 6) % 7;
      const startDate = new Date(this.calendarYear, this.calendarMonth, 1 - firstWeekday);
      const todayIso = todayISO();
      const days = [];
      for (let i = 0; i < 42; i++) {
        const d = new Date(startDate);
        d.setDate(startDate.getDate() + i);
        // Local ISO date (avoid timezone shift from toISOString in UTC)
        const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
        days.push({
          iso,
          day: d.getDate(),
          isCurrentMonth: d.getMonth() === this.calendarMonth,
          isToday: iso === todayIso,
          events: this.eventsOnDay(iso),
        });
      }
      return days;
    },

    eventsOnDay(iso) {
      return this.events.filter(e => {
        if (!e.date_start || !e.date_end) return false;
        if (iso < e.date_start || iso > e.date_end) return false;
        // Apply other filters but bypass date_range (calendar IS the date filter)
        return this.matches(e, { dateFrom: '', dateTo: '' });
      });
    },

    prevMonth() {
      if (this.calendarMonth === 0) {
        this.calendarMonth = 11;
        this.calendarYear -= 1;
      } else {
        this.calendarMonth -= 1;
      }
    },

    nextMonth() {
      if (this.calendarMonth === 11) {
        this.calendarMonth = 0;
        this.calendarYear += 1;
      } else {
        this.calendarMonth += 1;
      }
    },

    goToToday() {
      const now = new Date();
      this.calendarYear = now.getFullYear();
      this.calendarMonth = now.getMonth();
    },

    chipTextColor(hex) {
      if (!hex) return '#fff';
      const c = hex.replace('#', '');
      const r = parseInt(c.substr(0, 2), 16);
      const g = parseInt(c.substr(2, 2), 16);
      const b = parseInt(c.substr(4, 2), 16);
      const yiq = (r * 299 + g * 587 + b * 114) / 1000;
      return yiq >= 140 ? '#000' : '#fff';
    },

    initMap() {
      if (this.map) return;  // guard against double init
      this.map = L.map('map', { preferCanvas: true }).setView([50, 9], 4);

      const tileConfigs = {
        de: {
          url: 'https://{s}.tile.openstreetmap.de/{z}/{x}/{y}.png',
          attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors · Tiles by <a href="https://www.openstreetmap.de/">OSM Germany</a>',
          subdomains: 'abc',
          maxZoom: 18,
        },
        en: {
          url: 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png',
          attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors © <a href="https://carto.com/attributions">CARTO</a>',
          subdomains: 'abcd',
          maxZoom: 19,
        },
      };
      const cfg = tileConfigs[this.lang] || tileConfigs.en;
      L.tileLayer(cfg.url, {
        attribution: cfg.attribution,
        subdomains: cfg.subdomains,
        maxZoom: cfg.maxZoom,
      }).addTo(this.map);

      this.cluster = L.markerClusterGroup({
        showCoverageOnHover: false,
        maxClusterRadius: 50,
      });
      this.map.addLayer(this.cluster);
    },

    renderMarkers() {
      if (!this.cluster) return;
      this.cluster.clearLayers();
      const items = this.filtered.filter(e => e.location.lat && e.location.lon);
      // Group events that share a location into ONE marker. circleMarkers
      // can't be spiderfied by MarkerCluster, so co-located events would
      // overlap and only the top one would be clickable. One marker per
      // venue + a popup listing all its events sidesteps that entirely.
      const groups = new Map();
      for (const e of items) {
        const key = `${e.location.lat.toFixed(5)},${e.location.lon.toFixed(5)}`;
        if (!groups.has(key)) groups.set(key, []);
        groups.get(key).push(e);
      }
      const bounds = [];
      for (const list of groups.values()) {
        const e0 = list[0];
        const color = this.formats[e0.format]?.color || '#888';
        const marker = L.circleMarker([e0.location.lat, e0.location.lon], {
          radius: list.length > 1 ? 10 : 8,
          fillColor: color,
          color: '#fff',
          weight: 2,
          opacity: 1,
          fillOpacity: 0.9,
        });
        marker.bindPopup(this.popupForEvents(list), { closeButton: true });
        this.cluster.addLayer(marker);
        bounds.push([e0.location.lat, e0.location.lon]);
      }
      if (bounds.length > 0) {
        this.map.fitBounds(bounds, { padding: [40, 40], maxZoom: 8 });
      }
    },

    popupForEvents(list) {
      if (list.length === 1) return this.popupHtml(list[0]);
      const loc = list[0].location;
      const header = `${list.length} ${this.lang === 'de' ? 'Events an diesem Ort' : 'events at this location'}`;
      const place = `${this.escape(loc.city)}, ${loc.country}` +
        (loc.venue ? ` · ${this.escape(loc.venue)}` : '');
      const rows = list.map(e => {
        const fmt = this.formats[e.format]?.name || e.format;
        const dot = this.formats[e.format]?.color || '#888';
        let dr;
        if (!e.date_start) dr = this.tbaLabel;
        else if (e.date_start === e.date_end) dr = this.formatDate(e.date_start);
        else dr = `${this.formatDate(e.date_start)} – ${this.formatDate(e.date_end)}`;
        return `<li style="margin:.4em 0">` +
          `<span style="display:inline-block;width:.6em;height:.6em;border-radius:50%;background:${dot};margin-right:.35em;vertical-align:middle"></span>` +
          `<a href="${this.basePath}/${this.lang}/events/${e.slug}.html"><strong>${this.escape(e.name)}</strong></a>` +
          `<br><small style="color:#666">${dr} · ${this.escape(fmt)}</small></li>`;
      }).join('');
      return `<strong>${this.escape(header)}</strong><br>` +
        `<small>${place}</small>` +
        `<ul style="list-style:none;padding:0;margin:.5em 0 0">${rows}</ul>`;
    },

    popupHtml(e) {
      const formatName = this.formats[e.format]?.name || e.format;
      const venue = e.location.venue ? ` · ${e.location.venue}` : '';
      let dateRange;
      if (!e.date_start) {
        dateRange = this.tbaLabel;
      } else if (e.date_start === e.date_end) {
        dateRange = this.formatDate(e.date_start);
      } else {
        dateRange = `${this.formatDate(e.date_start)} – ${this.formatDate(e.date_end)}`;
      }
      const linkLabel = 'Details →';
      return `
        <strong>${this.escape(e.name)}</strong><br>
        <small>${dateRange}<br>${this.escape(e.location.city)}, ${e.location.country}${this.escape(venue)}</small><br>
        <small style="color:#666">${this.escape(formatName)}</small><br>
        <a href="${this.basePath}/${this.lang}/events/${e.slug}.html">${linkLabel}</a>
      `;
    },

    escape(s) {
      if (s == null) return '';
      return String(s)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;');
    },

    reset() {
      this.filters.formats = [];
      this.filters.regions = [...this.defaultRegions];
      this.filters.dateFrom = this.defaultDateFrom;
      this.filters.dateTo = this.defaultDateTo;
      this.search = '';
    },

    loadFromURL() {
      const p = new URLSearchParams(location.search);
      if (p.has('format')) this.filters.formats = p.get('format').split(',').filter(Boolean);
      if (p.has('region')) this.filters.regions = p.get('region').split(',').filter(Boolean);
      if (p.has('from')) this.filters.dateFrom = p.get('from');
      if (p.has('to')) this.filters.dateTo = p.get('to');
      if (p.has('q')) this.search = p.get('q');
      const viewParam = p.get('view');
      if (['list', 'map', 'calendar'].includes(viewParam)) this.view = viewParam;
    },

    saveToURL() {
      if (!this._initialized) return;
      const p = new URLSearchParams();
      if (this.filters.formats.length) p.set('format', this.filters.formats.join(','));
      if (!this.regionsAreDefault() && this.filters.regions.length) {
        p.set('region', this.filters.regions.join(','));
      }
      if (this.filters.dateFrom !== this.defaultDateFrom) p.set('from', this.filters.dateFrom);
      if (this.filters.dateTo !== this.defaultDateTo) p.set('to', this.filters.dateTo);
      if (this.search) p.set('q', this.search);
      if (this.view !== 'map') p.set('view', this.view);
      const qs = p.toString();
      history.replaceState(null, '', qs ? `?${qs}` : location.pathname);
    },
  };
}
