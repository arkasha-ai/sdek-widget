/**
 * SdekPvzWidget.js
 * Виджет выбора ПВЗ СДЭК с расчётом тарифа
 * Vue 3 + OpenLayers (через vue3-openlayers), Vite-билд
 */
import { createApp, h } from 'vue';
import 'ol/ol.css';
import PvzList from './components/PvzList.vue';
import MapPane from './components/MapPane.vue';
import './style.css';

export class SdekPvzWidget {
  /**
   * @param {Object} options
   * @param {string}          options.defaultLocation  — город для фокуса карты
   * @param {string}          options.fromLocation     — город отправления
   * @param {Array<Object>}   options.packages         — [{length,width,height,weight}]
   * @param {Function}        options.onChoose         — (type, tariff, address) => void
   * @param {string}         [options.backendUrl]      — URL sdek-backend.php
   */
  constructor(options = {}) {
    this.defaultLocation = options.defaultLocation || 'Москва';
    this.fromLocation    = options.fromLocation    || 'Москва';
    this.packages        = options.packages         || [];
    this.onChoose        = options.onChoose         || (() => {});
    this.backendUrl      = options.backendUrl       || './sdek-backend.php';
    console.log('[SdekPvzWidget] constructor options.backendUrl:', JSON.stringify(options.backendUrl), '→ this.backendUrl:', this.backendUrl);

    this._overlay   = null;
    this._app       = null;
    this._pvzAll    = [];
    this._isOpen    = false;
  }

  // ----------------------------------------------------------
  // Public API
  // ----------------------------------------------------------
  open() {
    if (this._isOpen) return;
    this._isOpen = true;
    this._mount();
    document.body.appendChild(this._overlay);
    this._loadInitial();
  }

  close() {
    if (!this._isOpen) return;
    this._isOpen = false;
    if (this._app) { this._app.unmount(); this._app = null; }
    if (this._overlay && this._overlay.parentNode) {
      this._overlay.parentNode.removeChild(this._overlay);
    }
    this._overlay = null;
    this._vm      = null;
    this._mapRef  = null;
    this._listRef = null;
  }

  // ----------------------------------------------------------
  // Mount Vue app (с vue3-openlayers)
  // ----------------------------------------------------------
  _mount() {
    this._overlay = document.createElement('div');
    this._overlay.className = 'sdwo-overlay';

    // ---- sort helper ----
    const sortByBounds = (pvzList, bounds) => {
      if (!bounds) return pvzList;
      const [minLon, minLat, maxLon, maxLat] = bounds;
      const clon = (minLon + maxLon) / 2;
      const clat = (minLat + maxLat) / 2;
      return [...pvzList].sort((a, b) => {
        const [la, lo] = a.location || [0, 0];
        const [lb, loB] = b.location || [0, 0];
        return Math.hypot(lo - clon, la - clat) - Math.hypot(loB - clon, lb - clat);
      }).map(p => {
        const [la, lo] = p.location || [0, 0];
        p._dist = (Math.hypot(lo - clon, la - clat) * 111).toFixed(1);
        return p;
      });
    };

    // данные reactive
    const vm = {
      list:      [],
      active:    null,
      loading:   true,
      listError: null,
      tariff:    null,
      pvz:       null,
      mapCenter: null,
      // ref к MapPane (устанавливается после mount)
      _mapRef:   null,
    };

    const self = this;

    this._app = createApp({
      components: { MapPane, PvzList },

      data: () => vm,

      methods: {
        async onMapSearch(q) {
          try {
            const geo = await self._fetch({ action: 'geocode', query: q });
            if (geo.lat && geo.lon) {
              this.mapCenter = [parseFloat(geo.lat), parseFloat(geo.lon)];
            } else {
              this._mapRef?.flashError('Адрес не найден');
            }
          } catch (err) {
            this._mapRef?.flashError(err.message);
          }
        },

        async onMapMoveend(bounds) {
          if (!bounds) return;
          const [minLon, minLat, maxLon, maxLat] = bounds;
          const visible = self._pvzAll.filter(p => {
            const [la, lo] = p.location || [];
            if (!lo || !la) return false;
            return lo >= minLon && lo <= maxLon && la >= minLat && la <= maxLat;
          });
          this.list = sortByBounds(visible, bounds);
        },

        onMarkerSelect(code) {
          const pvz = self._pvzAll.find(p => p.code == code);
          if (pvz) self._selectPvz(pvz);
        },

        async onPvzSelect(pvz) {
          await self._selectPvz(pvz);
        },

        onChoose(pvz, tariff) {
          self.onChoose('PVZ', tariff, pvz);
          self.close();
        },

        close() {
          self.close();
        },
      },

      // render-функция вместо inline template (не требует runtime compiler)
      render() {
        return h('div', { class: 'sdwo-popup' }, [
          h('div', { class: 'sdwo-popup__header' }, [
            h('span', { class: 'sdwo-popup__title' }, 'Выбор ПВЗ СДЭК'),
            h('button', {
              class: 'sdwo-popup__close',
              onClick: () => this.close(),
            }, '\u00D7'),
          ]),
          console.log('[SdekPvzWidget] render MapPane props — backendUrl:', this.backendUrl, 'mapCenter:', this.mapCenter, 'list length:', this.list.length);
          h('div', { class: 'sdwo-popup__body' }, [
            h(MapPane, {
              ref: 'mapRef',
              center:     this.mapCenter,
              zoom:       12,
              markers:    this.list,
              activeCode: this.active,
              backendUrl: this.backendUrl,
              onSearch:       this.onMapSearch,
              onMoveend:      this.onMapMoveend,
              onMarkerselect: this.onMarkerSelect,
            }),
            h(PvzList, {
              list:    this.list,
              active:  this.active,
              loading: this.loading,
              error:   this.listError,
              tariff:  this.tariff,
              pvz:     this.pvz,
              onSelect: this.onPvzSelect,
              onChoose: this.onChoose,
            }),
          ]),
        ]);
      },
    });

    this._app.mount(this._overlay);

    // получаем корневой Vue instance и ref на MapPane
    const root = this._app._instance.proxy;
    this._vm    = root;
    this._mapRef = root.$refs.mapRef || null;

    // кнопка закрытия — вешаем обработчик сразу на DOM
    this._overlay.querySelector('.sdwo-popup__close')
      .addEventListener('click', () => this.close());
  }

  // ----------------------------------------------------------
  // Data loading
  // ----------------------------------------------------------
  async _loadInitial() {
    if (!this._vm) return;
    this._vm.loading   = true;
    this._vm.listError = null;

    try {
      const geo = await this._fetch({ action: 'geocode', query: this.defaultLocation });
      if (geo.lat && geo.lon) {
        this._vm.mapCenter = [parseFloat(geo.lat), parseFloat(geo.lon)];
      }
      await this._reloadPvz();
    } catch (err) {
      this._vm.listError = 'Ошибка загрузки: ' + err.message;
    } finally {
      this._vm.loading = false;
    }
  }

  async _reloadPvz() {
    if (!this._vm) return;
    this._vm.loading = true;

    try {
      const data = await this._fetch({ action: 'pvzlist', country_code: 'RU' });
      const list = Array.isArray(data) ? data : (data.list || data.pvz || []);
      this._pvzAll = list;
      const bounds = this._mapRef?.getBounds?.();
      if (bounds) {
        const [minLon, minLat, maxLon, maxLat] = bounds;
        const clon = (minLon + maxLon) / 2;
        const clat = (minLat + maxLat) / 2;
        const visible = list.filter(p => {
          const [la, lo] = p.location || [];
          return lo >= minLon && lo <= maxLon && la >= minLat && la <= maxLat;
        });
        this._vm.list = [...visible].sort((a, b) => {
          const [la, lo] = a.location || [0, 0];
          const [lb, loB] = b.location || [0, 0];
          return Math.hypot(lo - clon, la - clat) - Math.hypot(loB - clon, lb - clat);
        }).map(p => {
          const [la, lo] = p.location || [0, 0];
          p._dist = (Math.hypot(lo - clon, la - clat) * 111).toFixed(1);
          return p;
        });
      } else {
        this._vm.list = list;
      }
    } catch (err) {
      this._vm.listError = 'Ошибка загрузки ПВЗ: ' + err.message;
    } finally {
      this._vm.loading = false;
    }
  }

  async _selectPvz(pvz) {
    if (!this._vm) return;
    this._chosenPvz = pvz;
    this._vm.pvz    = pvz;
    this._vm.active = pvz.code;
    this._vm.tariff = null;

    // Фокусируем карту на выбранном ПВЗ (zoom ~17 ≈ вид здания)
    if (this._mapRef && pvz.location) {
      this._mapRef.panTo(pvz.location, 17);
    }

    try {
      const tariff = await this._fetch({
        action:      'calculate',
        from_city:   this.fromLocation,
        to_pvz_code: pvz.city_code || pvz.code,  // CDEK tariff needs city_code, fallback to pvz.code
        packages:    JSON.stringify(this.packages),
      });
      this._vm.tariff = tariff;
    } catch (err) {
      console.error('[SdekPvzWidget] tariff error:', err);
    }
  }

  // ----------------------------------------------------------
  // Fetch helper
  // ----------------------------------------------------------
  async _fetch(params) {
    const url  = this.backendUrl + '?' + new URLSearchParams(params).toString();
    const res  = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    if (json.error) throw new Error(json.error);
    return json;
  }
}

// Глобальный экспорт для UMD <script>-тега
if (typeof window !== 'undefined') {
  window.SdekPvzWidget = SdekPvzWidget;
}
