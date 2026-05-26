function eventFilter() {
  return {
    events: [],
    formats: window.FORMATS || {},
    regions: window.REGIONS || [],
    lang: window.LANG || 'de',
    locale: window.LOCALE || 'de-DE',
    defaultRegions: window.DEFAULT_REGIONS || ['dach'],
    basePath: window.BASE_PATH || '',
    tbaLabel: window.DATE_TBA_LABEL || 'TBA',
    filters: {
      formats: [],
      regions: [],
      showPast: false,
    },
    search: '',
    view: 'map',
    map: null,
    cluster: null,
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
          // Defer renderMarkers + invalidateSize until CSS layout is settled.
          // On initial page load Leaflet can otherwise measure 0×0 px and
          // render nothing.
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
      if (this.filters.showPast) n++;
      return n;
    },

    matches(e, overrides = {}) {
      const today = new Date().toISOString().slice(0, 10);
      const formats = overrides.formats ?? this.filters.formats;
      const regions = overrides.regions ?? this.filters.regions;
      const showPast = overrides.showPast ?? this.filters.showPast;
      const search = (overrides.search ?? this.search).toLowerCase().trim();

      // TBA events (date_end null) are never "past" — always visible.
      if (!showPast && e.date_end && e.date_end < today) return false;
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

    initMap() {
      this.map = L.map('map', { preferCanvas: true }).setView([50, 9], 4);

      // Tile provider varies by language: OSM Germany has German place
      // labels (München, Köln); CARTO Voyager has English (Munich, Cologne).
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
      const bounds = [];
      for (const e of items) {
        const color = this.formats[e.format]?.color || '#888';
        const marker = L.circleMarker([e.location.lat, e.location.lon], {
          radius: 8,
          fillColor: color,
          color: '#fff',
          weight: 2,
          opacity: 1,
          fillOpacity: 0.9,
        });
        marker.bindPopup(this.popupHtml(e), { closeButton: true });
        this.cluster.addLayer(marker);
        bounds.push([e.location.lat, e.location.lon]);
      }
      if (bounds.length > 0) {
        this.map.fitBounds(bounds, { padding: [40, 40], maxZoom: 8 });
      }
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
      this.filters.showPast = false;
      this.search = '';
    },

    loadFromURL() {
      const p = new URLSearchParams(location.search);
      if (p.has('format')) this.filters.formats = p.get('format').split(',').filter(Boolean);
      if (p.has('region')) this.filters.regions = p.get('region').split(',').filter(Boolean);
      if (p.has('q')) this.search = p.get('q');
      if (p.get('past') === '1') this.filters.showPast = true;
      const viewParam = p.get('view');
      if (viewParam === 'list' || viewParam === 'map') this.view = viewParam;
    },

    saveToURL() {
      if (!this._initialized) return;
      const p = new URLSearchParams();
      if (this.filters.formats.length) p.set('format', this.filters.formats.join(','));
      if (!this.regionsAreDefault() && this.filters.regions.length) {
        p.set('region', this.filters.regions.join(','));
      }
      if (this.search) p.set('q', this.search);
      if (this.filters.showPast) p.set('past', '1');
      if (this.view !== 'map') p.set('view', this.view);
      const qs = p.toString();
      history.replaceState(null, '', qs ? `?${qs}` : location.pathname);
    },
  };
}
