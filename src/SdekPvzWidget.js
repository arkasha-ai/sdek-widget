/**
 * SdekPvzWidget.js
 * Виджет выбора ПВЗ СДЭК с расчётом тарифа
 * Дизайн и UX повторяют оригинальный виджет СДЭК v3
 * Vue 3 + OpenLayers, Vite-билд
 */
import { createApp, h } from 'vue';
import 'ol/ol.css';
import SegmentedControl from './components/SegmentedControl.vue';
import MapPane from './components/MapPane.vue';
import PvzList from './components/PvzList.vue';
import PvzDetail from './components/PvzDetail.vue';
import DoorPanel from './components/DoorPanel.vue';
import './style.css';

const FETCH_TIMEOUT_MS = 15000;

/**
 * Сортирует ПВЗ по расстоянию от центра bbox.
 * Возвращает shallow-клоны с полем _dist (км). Не мутирует оригиналы.
 */
function sortByBounds(pvzList, bounds) {
  if (!bounds) return pvzList;
  const [minLon, minLat, maxLon, maxLat] = bounds;
  const clon = (minLon + maxLon) / 2;
  const clat = (minLat + maxLat) / 2;
  return [...pvzList]
    .map(p => {
      const [la, lo] = p.location || [0, 0];
      const d = Math.hypot(lo - clon, la - clat);
      return { ...p, _dist: (d * 111).toFixed(1), _d: d };
    })
    .sort((a, b) => a._d - b._d)
    .map(({ _d, ...rest }) => rest);
}

export class SdekPvzWidget {
  /**
   * @param {Object} options
   * @param {string}          options.defaultLocation  — город для фокуса карты
   * @param {string}          options.fromLocation     — город отправления
   * @param {Array<Object>}   options.packages         — [{length,width,height,weight}]
   * @param {Function}        options.onChoose         — (mode, tariff, target) => void
   * @param {string}         [options.backendUrl]      — URL sdek-backend.php
   * @param {boolean}        [options.officeVisibleTab]   — видимость кнопки "До пункта выдачи"
   * @param {boolean}        [options.doorVisibleTab]     — видимость кнопки "До двери"
   */
  constructor(options = {}) {
    this.defaultLocation = options.defaultLocation || 'Москва';
    this.fromLocation    = options.fromLocation    || 'Москва';
    this.packages        = options.packages        || [];
    this.onChoose        = options.onChoose        || (() => {});
    this.backendUrl      = options.backendUrl      || './sdek-backend.php';
    this.officeVisible   = options.officeVisibleTab;
    this.doorVisible     = options.doorVisibleTab;

    this._overlay = null;
    this._app     = null;
    this._pvzAll  = [];
    this._isOpen  = false;
  }

  // ----------------------------------------------------------
  // Public API
  // ----------------------------------------------------------
  open() {
    if (this._isOpen) return;
    this._isOpen = true;
    this._mount();
    this._loadInitial();
  }

  close() {
    if (!this._isOpen) return;
    this._isOpen = false;
    if (this._app) { this._app.unmount(); this._app = null; }
    if (this._overlay?.parentNode) this._overlay.parentNode.removeChild(this._overlay);
    this._overlay = null;
    this._vm      = null;
    this._mapRef  = null;
  }

  // ----------------------------------------------------------
  // Mount Vue app
  // ----------------------------------------------------------
  _mount() {
    this._overlay = document.createElement('div');
    this._overlay.className = 'sdwo-overlay';
    document.body.appendChild(this._overlay);

    const self = this;

    this._app = createApp({
      components: { SegmentedControl, MapPane, PvzList, PvzDetail, DoorPanel },

      data: () => ({
        // State machine
        mode:       this.doorVisible && !this.officeVisible ? 'door' : 'office', // 'office' | 'door'
        panel:      'list',      // 'list' | 'detail' | 'none'
        panelOpen:  window.innerWidth > 555,  // на мобильных скрыта по умолчанию

        // Office mode
        list:       [],
        active:     null,
        loading:    true,
        listError:  null,
        pvz:        null,        // выбранный ПВЗ
        tariffs:    [],          // массив тарифов для выбранного ПВЗ
        tariffLoading: false,
        tariffError:   null,

        // Door mode
        doorAddress:  null,
        doorHint:     null,
        doorLocation: null,
        doorCityCode: null,
        doorTariffs:  [],
        doorLoading:  false,
        doorError:    null,

        // Map
        mapCenter:  null,

        // Filters
        filters: { pvz: true, postamat: true, cash: false, cashless: false, dressing: false },
        lastBounds: null,
      }),

      methods: {
        // --- Mode ---
        onModeChange(mode) {
          this.mode = mode;
          if (mode === 'office') {
            this.panel = 'list';
            this.panelOpen = true;
          } else {
            this.panel = 'none';
            this.panelOpen = true;
            this.doorAddress = null;
            this.doorTariffs = [];
          }
        },

        // --- Filters ---
        onFilterChange(f) {
          this.filters = f;
          // Перефильтровать с последними bounds
          if (this.lastBounds) this.onMapMoveend(this.lastBounds);
        },

        _applyFilters(list) {
          return list.filter(p => {
            const type = (p.type || 'PVZ').toUpperCase();
            if (type === 'PVZ' && !this.filters.pvz) return false;
            if (type === 'POSTAMAT' && !this.filters.postamat) return false;
            if (this.filters.cash && !p.have_cash) return false;
            if (this.filters.cashless && !p.have_cashless) return false;
            if (this.filters.dressing && !p.is_dressing_room) return false;
            return true;
          });
        },

        // --- Map events ---
        onMapMoveend(bounds) {
          if (!bounds) return;
          this.lastBounds = bounds;
          const [minLon, minLat, maxLon, maxLat] = bounds;
          const visible = self._pvzAll.filter(p => {
            const [la, lo] = p.location || [];
            if (!lo || !la) return false;
            return lo >= minLon && lo <= maxLon && la >= minLat && la <= maxLat;
          });
          this.list = sortByBounds(this._applyFilters(visible), bounds);
        },

        onMarkerSelect(code) {
          const pvz = self._pvzAll.find(p => p.code == code);
          if (pvz) this.selectPvz(pvz);
        },

        togglePanel() {
          this.panelOpen = !this.panelOpen;
        },

        // --- Office: select PVZ ---
        async selectPvz(pvz) {
          this.pvz = pvz;
          this.active = pvz.code;
          this.panel = 'detail';
          this.panelOpen = true;
          this.tariffs = [];
          this.tariffLoading = true;
          this.tariffError = null;

          // Pan map
          if (self._mapRef && pvz.location) {
            self._mapRef.panTo(pvz.location, 17);
          }

          try {
            const resp = await self._fetch({
              action:      'calculate',
              from_city:   self.fromLocation,
              to_pvz_code: pvz.city_code || pvz.code,
              packages:    JSON.stringify(self.packages),
            }, { method: 'POST' });
            this.tariffs = resp.tariff_codes || [];
          } catch (err) {
            this.tariffError = err.message;
          } finally {
            this.tariffLoading = false;
          }
        },

        backToList() {
          this.panel = 'list';
          this.pvz = null;
          this.tariffs = [];
        },

        onPvzChoose(pvz, tariff) {
          try {
            self.onChoose('office', tariff, pvz);
          } catch (e) {
            console.error('[SdekPvzWidget] onChoose error:', e);
          } finally {
            self.close();
          }
        },

        // --- Door mode ---
        async onMapClick(latLon) {
          if (this.mode !== 'door') return;
          this.doorLoading = true;
          this.doorAddress = null;
          this.doorTariffs = [];
          this.doorError = null;
          this.doorHint = null;
          this.panel = 'none';
          this.panelOpen = true;

          try {
            const geo = await self._fetch({
              action: 'reverse_geocode',
              lat: latLon[0],
              lon: latLon[1],
            });
            this.doorAddress  = geo.address || null;
            this.doorLocation = [parseFloat(geo.lat), parseFloat(geo.lon)];
            this.doorCityCode = geo.city_code || null;

            // Только если точность >= street — запрашиваем тарифы
            if (geo.precision === 'house' || geo.precision === 'street') {
              if (geo.city_code) {
                const resp = await self._fetch({
                  action:      'calculate',
                  from_city:   self.fromLocation,
                  to_pvz_code: geo.city_code,
                  packages:    JSON.stringify(self.packages),
                }, { method: 'POST' });
                // Фильтруем door-тарифы (delivery_mode 1,3,5,7 — дверь)
                const doorModes = [1, 3, 5, 7];
                this.doorTariffs = (resp.tariff_codes || []).filter(
                  t => t.delivery_mode == null || doorModes.includes(t.delivery_mode)
                );
              } else {
                this.doorHint = 'Не удалось определить город';
              }
            } else {
              this.doorHint = 'Выберите адрес точнее (кликните ближе к зданию)';
            }
          } catch (err) {
            this.doorError = err.message;
          } finally {
            this.doorLoading = false;
          }
        },

        onDoorChoose(target, tariff) {
          try {
            self.onChoose('door', tariff, target);
          } catch (e) {
            console.error('[SdekPvzWidget] onChoose error:', e);
          } finally {
            self.close();
          }
        },

        close() { self.close(); },
      },

      // --- Render function (без template compiler) ---
      render() {
        const children = [];

        // 1. Segmented Control
        children.push(
          h(SegmentedControl, {
            modelValue: this.mode,
            officeVisible: self.officeVisible,
            doorVisible: self.doorVisible,
            'onUpdate:modelValue': this.onModeChange,
            onTogglepanel: this.togglePanel,
            onClose: () => this.close(),
          })
        );

        // 3. Map container (position relative для overlay панелей)
        const mapChildren = [];

        // 3a. Map
        mapChildren.push(
          h(MapPane, {
            ref: 'mapRef',
            center:     this.mapCenter,
            zoom:       12,
            markers:    this.mode === 'office' ? this.list : [],
            activeCode: this.active,
            backendUrl: self.backendUrl,
            mode:       this.mode,
            panelOpen:  this.panelOpen,
            onMoveend:      this.onMapMoveend,
            onMarkerselect: this.onMarkerSelect,
            onMapclick:     this.onMapClick,
            onFilterchange: this.onFilterChange,
            onTogglepanel:  this.togglePanel,
          })
        );

        // 3b. Office panels
        if (this.mode === 'office') {
          // PvzList
          mapChildren.push(
            h(PvzList, {
              visible: this.panelOpen && this.panel === 'list',
              list:    this.list,
              active:  this.active,
              loading: this.loading,
              error:   this.listError,
              onSelect: (pvz) => this.selectPvz(pvz),
            })
          );

          // PvzDetail
          mapChildren.push(
            h(PvzDetail, {
              visible:  this.panelOpen && this.panel === 'detail',
              pvz:      this.pvz,
              tariffs:  this.tariffs,
              loading:  this.tariffLoading,
              error:    this.tariffError,
              onBack:   () => this.backToList(),
              onChoose: this.onPvzChoose,
            })
          );
        }

        // 3c. Door panel
        if (this.mode === 'door') {
          mapChildren.push(
            h(DoorPanel, {
              visible:  this.panelOpen,
              address:  this.doorAddress,
              hint:     this.doorHint,
              tariffs:  this.doorTariffs,
              loading:  this.doorLoading,
              error:    this.doorError,
              location: this.doorLocation,
              cityCode: this.doorCityCode,
              onChoose: this.onDoorChoose,
            })
          );
        }

        children.push(
          h('div', { class: 'sdwo-map-wrap' }, mapChildren)
        );

        // 4. Modal Close
        const closeBtn = h('button', {
          class: 'sdwo-modal-close',
          title: 'Закрыть',
          onClick: () => this.close()
        }, [
          h('svg', {
            width: '20',
            height: '20',
            viewBox: '0 0 24 24',
            fill: 'none',
            stroke: 'currentColor',
            'stroke-width': '2',
            'stroke-linecap': 'round',
            'stroke-linejoin': 'round'
          }, [
            h('line', { x1: '18', y1: '6', x2: '6', y2: '18' }),
            h('line', { x1: '6', y1: '6', x2: '18', y2: '18' })
          ])
        ]);

        return h('div', { class: 'sdwo-popup' }, [...children, closeBtn]);
      },
    });

    this._app.mount(this._overlay);

    const root = this._app._instance.proxy;
    this._vm     = root;
    this._mapRef = root.$refs.mapRef || null;
  }

  // ----------------------------------------------------------
  // Data loading
  // ----------------------------------------------------------
  async _loadInitial() {
    if (!this._vm) return;
    this._vm.loading   = true;
    this._vm.listError = null;

    const geocodePromise = this._fetch({ action: 'geocode', query: this.defaultLocation })
      .then(geo => {
        if (geo.lat && geo.lon && this._vm) {
          this._vm.mapCenter = [parseFloat(geo.lat), parseFloat(geo.lon)];
        }
      })
      .catch(err => console.warn('[SdekPvzWidget] geocode failed:', err.message));

    try {
      await Promise.all([geocodePromise, this._reloadPvz()]);
    } catch (err) {
      if (this._vm) this._vm.listError = 'Ошибка загрузки: ' + err.message;
    } finally {
      if (this._vm) this._vm.loading = false;
    }
  }

  async _reloadPvz() {
    if (!this._vm) return;

    try {
      let page = 0;
      let list, data;
      this._pvzAll = [];
      do {
        data = await this._fetch({action: 'pvzlist', country_code: 'RU', size: 500, page});
        list = Array.isArray(data) ? data : (data.items || data.pvz || []);
        this._pvzAll = [...this._pvzAll, ...list];
        page++;
      } while ((data.total_pages ?? 0) > page);


      const bounds = this._mapRef?.getBounds?.();
      if (bounds) {
        const [minLon, minLat, maxLon, maxLat] = bounds;
        const visible = list.filter(p => {
          const [la, lo] = p.location || [];
          return lo >= minLon && lo <= maxLon && la >= minLat && la <= maxLat;
        });
        this._vm.list = sortByBounds(visible, bounds);
      } else {
        this._vm.list = list;
      }
    } catch (err) {
      if (this._vm) this._vm.listError = 'Ошибка загрузки ПВЗ: ' + err.message;
    }
  }

  // ----------------------------------------------------------
  // Fetch helper
  // ----------------------------------------------------------
  async _fetch(params, { method = 'GET' } = {}) {
    const signal = AbortSignal.timeout(FETCH_TIMEOUT_MS);

    let url, init;
    if (method === 'POST') {
      url  = this.backendUrl;
      init = {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams(params).toString(),
        signal,
      };
    } else {
      url  = this.backendUrl + '?' + new URLSearchParams(params).toString();
      init = { signal };
    }

    let res;
    try {
      res = await fetch(url, init);
    } catch (err) {
      if (err.name === 'TimeoutError' || err.name === 'AbortError') {
        throw new Error('Таймаут запроса');
      }
      throw err;
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    if (json.error) throw new Error(json.error);
    return json;
  }
}

