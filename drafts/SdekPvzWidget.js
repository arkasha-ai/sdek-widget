/**
 * SdekPvzWidget.js
 * Виджет выбора ПВЗ СДЭК с расчётом тарифа
 * Vue 3 (CDN) + OpenLayers 9, ES module, без сборки
 *
 * Пример использования:
 * <script src="SdekPvzWidget.js">< /script>
 * <script>
 *   const widget = new SdekPvzWidget({
 *     defaultLocation: 'Краснокамск',
 *     fromLocation: 'Челябинск',
 *     packages: [{ length: 30, width: 20, height: 15, weight: 1000 }],
 *     onChoose: (type, tariff, address) => {
 *       console.log('Выбран ПВЗ:', address, 'Тариф:', tariff);
 *     }
 *   });
 *   widget.open();
 * < /script>
 */

(function (global) {
  'use strict';

  // ================================================================
  // SdekPvzWidget
  // ================================================================
  class SdekPvzWidget {
    /**
     * @param {Object} options
     * @param {string}          options.defaultLocation  — город для фокуса карты при открытии
     * @param {string}          options.fromLocation     — город отправления
     * @param {Array<Object>}   options.packages         — [{length, width, height, weight}]
     * @param {Function}        options.onChoose         — callback(type, tariff, address)
     * @param {string}          [options.backendUrl]     — URL sdek-backend.php
     */
    constructor(options = {}) {
      this.defaultLocation = options.defaultLocation || 'Москва';
      this.fromLocation    = options.fromLocation    || 'Москва';
      this.packages         = options.packages         || [];
      this.onChoose         = options.onChoose         || (() => {});
      this.backendUrl       = options.backendUrl       || './sdek-backend.php';

      // внутреннее состояние
      this._popup       = null;
      this._vueApp      = null;
      this._map         = null;
      this._mapReady    = false;
      this._pvzAll      = [];       // все ПВЗ (кеш)
      this._chosenPvz   = null;
      this._tariff      = null;
      this._searchTimer = null;
      this._moveTimer   = null;
      this._isOpen      = false;

      // стили инъектятся один раз
      if (!document.getElementById('sdw-styles')) {
        const s = document.createElement('style');
        s.id = 'sdw-styles';
        s.textContent = this._css();
        document.head.appendChild(s);
      }
    }

    // ----------------------------------------------------------
    // Public API
    // ----------------------------------------------------------
    open() {
      if (this._isOpen) return;
      this._isOpen = true;
      this._buildDOM();
      document.body.appendChild(this._popup);
      this._bootVue();
      this._bootMap();
      this._loadInitial();
    }

    close() {
      if (!this._isOpen) return;
      this._isOpen = false;
      if (this._vueApp) { this._vueApp.unmount(); this._vueApp = null; }
      if (this._map)    { this._map.setTarget(null); this._map = null; }
      if (this._popup && this._popup.parentNode) {
        this._popup.parentNode.removeChild(this._popup);
      }
      this._popup    = null;
      this._chosenPvz = null;
      this._tariff    = null;
    }

    // ----------------------------------------------------------
    // DOM-построение
    // ----------------------------------------------------------
    _buildDOM() {
      this._popup = document.createElement('div');
      this._popup.className = 'sdw-overlay';
      this._popup.innerHTML = `
        <div class="sdw-popup">
          <div class="sdw-popup__header">
            <span class="sdw-popup__title">Выбор ПВЗ СДЭК</span>
            <button class="sdw-popup__close" id="sdw-close" aria-label="Закрыть">&times;</button>
          </div>
          <div class="sdw-popup__body">
            <!-- Левая часть: карта -->
            <div class="sdw-map-col">
              <div class="sdw-search-row">
                <input
                  type="text"
                  id="sdw-search"
                  class="sdw-input"
                  placeholder="Поиск адреса…"
                  autocomplete="off"
                />
                <div class="sdw-error" id="sdw-search-error" hidden></div>
              </div>
              <div id="sdw-map" class="sdw-map"></div>
            </div>
            <!-- Правая часть: панель Vue -->
            <div class="sdw-sidebar" id="sdw-sidebar">
              <div class="sdw-sidebar__head">
                <span>ПВЗ в видимой области</span>
                <span class="sdw-badge" id="sdw-count">0</span>
              </div>
              <div class="sdw-sidebar__err" id="sdw-list-error" hidden></div>
              <div class="sdw-sidebar__list" id="sdw-pvz-list"></div>
              <div class="sdw-tariff" id="sdw-tariff-block" hidden>
                <div class="sdw-tariff__label">Стоимость доставки</div>
                <div class="sdw-tariff__price" id="sdw-tariff-price">—</div>
                <div class="sdw-tariff__days"  id="sdw-tariff-days">—</div>
              </div>
              <div class="sdw-sidebar__foot">
                <button class="sdw-btn" id="sdw-choose-btn" disabled>Выбрать</button>
              </div>
            </div>
          </div>
        </div>
      `;
    }

    // ----------------------------------------------------------
    // Vue 3 (CDN) — реактивная панель
    // ----------------------------------------------------------
    _bootVue() {
      const listEl  = document.getElementById('sdw-pvz-list');
      const countEl = document.getElementById('sdw-count');
      const errEl   = document.getElementById('sdw-list-error');
      const tariffBlock = document.getElementById('sdw-tariff-block');
      const tariffPrice = document.getElementById('sdw-tariff-price');
      const tariffDays  = document.getElementById('sdw-tariff-days');
      const chooseBtn = document.getElementById('sdw-choose-btn');
      const closeBtn = document.getElementById('sdw-close');
      const searchEl = document.getElementById('sdw-search');
      const searchErr = document.getElementById('sdw-search-error');

      // --- reactive state (Proxy) ---
      const state = {
        list:     [],   // видимые ПВЗ
        active:   null, // code выбранного
        loading:  false,
        tariff:   null,
        pvz:      null,
      };

      const render = () => {
        countEl.textContent = state.list.length;

        // error / loading
        if (state.loading) {
          listEl.innerHTML = [1,2,3].map(() =>
            `<div class="sdw-skeleton"></div>`
          ).join('');
          return;
        }
        if (errEl.hidden === false) {
          listEl.innerHTML = '';
          return;
        }

        if (!state.list.length) {
          listEl.innerHTML = `<div class="sdw-empty">ПВЗ не найдены</div>`;
          return;
        }

        listEl.innerHTML = state.list.map(p => `
          <div class="sdw-pvz-item${state.active === p.code ? ' sdw-pvz-item--active' : ''}"
               data-code="${this._h(p.code)}">
            <div class="sdw-pvz-item__name">${this._h(p.name || p.address)}</div>
            <div class="sdw-pvz-item__addr">${this._h(p.address)}</div>
            <div class="sdw-pvz-item__time">${this._h(p.work_time || '')}</div>
            ${p._dist ? `<div class="sdw-pvz-item__dist">~ ${this._h(p._dist)} км</div>` : ''}
          </div>
        `).join('');

        // обработка кликов
        listEl.querySelectorAll('.sdw-pvz-item').forEach(el => {
          el.addEventListener('click', () => {
            const code = el.dataset.code;
            const pvz  = state.list.find(p => p.code == code);
            if (pvz) this._selectPvz(pvz);
          });
        });

        // тариф
        if (state.tariff) {
          tariffBlock.hidden = false;
          tariffPrice.textContent = (state.tariff.price ?? state.tariff.delivery_sum ?? '—') + ' ₽';
          const min = state.tariff.period_min ?? '?';
          const max = state.tariff.period_max ?? '?';
          tariffDays.textContent  = `Срок: ${min}–${max} дн.`;
        } else {
          tariffBlock.hidden = true;
        }

        chooseBtn.disabled = !(state.pvz && state.tariff);
      };

      // Proxy-обёртка для авто-рендера при мутациях
      const PROPS = new Set(['list','active','loading','tariff','pvz']);
      this._vue = new Proxy(state, {
        set(t, k, v) { t[k] = v; if (PROPS.has(k)) render(); return true; }
      });

      // --- events ---
      closeBtn.addEventListener('click', () => this.close());
      chooseBtn.addEventListener('click', () => {
        if (!state.pvz || !state.tariff) return;
        this.onChoose('PVZ', state.tariff, state.pvz);
        this.close();
      });

      searchEl.addEventListener('input', e => {
        clearTimeout(this._searchTimer);
        const q = e.target.value.trim();
        if (q.length < 3) return;
        searchErr.hidden = true;
        this._searchTimer = setTimeout(() => this._geocodeSearch(q, searchErr), 400);
      });

      render();
    }

    // ----------------------------------------------------------
    // OpenLayers
    // ----------------------------------------------------------
    _bootMap() {
      const mapEl = document.getElementById('sdw-map');

      const loadOl = () => new Promise(resolve => {
        if (window.ol) { resolve(); return; }
        const link = document.createElement('link');
        link.rel   = 'stylesheet';
        link.href  = 'https://cdn.jsdelivr.net/npm/ol@9.2.4/ol.css';
        document.head.appendChild(link);

        const script = document.createElement('script');
        script.src   = 'https://cdn.jsdelivr.net/npm/ol@9.2.4/dist/ol.js';
        script.onload = resolve;
        document.body.appendChild(script);
      });

      loadOl().then(() => this._initMap(mapEl));
    }

    _initMap(mapEl) {
      const { Map, View, Layer, TileLayer, Source, OSM,
              layer: { Vector: VecLayer }, source: { Vector: VecSrc },
              Feature, geom: { Point } } = window.ol;
      const { fromLonLat, toLonLat } = window.ol.proj;
      const { Style, Circle: Cls, Fill, Stroke, Text } = window.ol.style;

      this._mapLayer = new VecLayer({ source: new VecSrc() });
      this._map = new Map({
        target: mapEl,
        layers: [
          new TileLayer({ source: new OSM() }),
          this._mapLayer,
        ],
        view: new View({
          center: fromLonLat([37.6176, 55.7558]),
          zoom: 10,
        }),
      });

      // клик по маркеру
      this._map.on('click', evt => {
        const feature = this._map.forEachFeatureAtPixel(evt.pixel, f => f);
        if (!feature) return;
        const code = feature.getId();
        const pvz  = this._pvzAll.find(p => p.code == code);
        if (pvz) this._selectPvz(pvz);
      });

      // перемещение карты → обновить список
      this._map.on('moveend', () => {
        clearTimeout(this._moveTimer);
        this._moveTimer = setTimeout(() => this._updateVisiblePvz(), 350);
      });

      this._mapReady = true;
    }

    // ----------------------------------------------------------
    // Загрузка данных
    // ----------------------------------------------------------
    async _loadInitial() {
      this._vue.loading = true;
      try {
        // геокодируем defaultLocation
        const geo = await this._fetch({ action: 'geocode', query: this.defaultLocation });
        if (geo.lat && geo.lon && this._map) {
          const { fromLonLat } = window.ol.proj;
          this._map.getView().setCenter(
            fromLonLat([parseFloat(geo.lon), parseFloat(geo.lat)])
          );
          this._map.getView().setZoom(12);
        }
        // загружаем все ПВЗ
        await this._reloadPvz();
      } catch (err) {
        console.error('[SdekPvzWidget] init error:', err);
      } finally {
        this._vue.loading = false;
      }
    }

    async _reloadPvz() {
      this._vue.loading = true;
      const errEl = document.getElementById('sdw-list-error');
      errEl.hidden = true;

      try {
        const data = await this._fetch({ action: 'pvzlist', country_code: 'RU' });
        const list = Array.isArray(data) ? data : (data.list || data.pvz || []);
        this._pvzAll = list;
        await this._updateVisiblePvz();
        this._renderMarkers(list);
      } catch (err) {
        errEl.textContent = 'Ошибка загрузки ПВЗ: ' + err.message;
        errEl.hidden = false;
      } finally {
        this._vue.loading = false;
      }
    }

    async _geocodeSearch(query, errEl) {
      errEl.hidden = true;
      try {
        const geo = await this._fetch({ action: 'geocode', query });
        if (!geo.lat || !geo.lon) {
          errEl.textContent = 'Адрес не найден';
          errEl.hidden = false;
          return;
        }
        if (this._map) {
          const { fromLonLat } = window.ol.proj;
          this._map.getView().setCenter(
            fromLonLat([parseFloat(geo.lon), parseFloat(geo.lat)])
          );
          this._map.getView().setZoom(12);
        }
        await this._reloadPvz();
      } catch (err) {
        errEl.textContent = err.message;
        errEl.hidden = false;
      }
    }

    // ----------------------------------------------------------
    // Расчёт тарифа
    // ----------------------------------------------------------
    async _selectPvz(pvz) {
      this._chosenPvz = pvz;
      this._vue.pvz   = pvz;
      this._vue.active = pvz.code;
      this._vue.tariff = null;

      // центрируем карту
      if (this._map && pvz.location) {
        const [lat, lon] = pvz.location;
        const { toLonLat } = window.ol.proj;
        this._map.getView().setCenter(toLonLat([lon, lat]));
      }

      // запрос тарифа
      try {
        const tariff = await this._fetch({
          action:       'calculate',
          from_city:    this.fromLocation,
          to_pvz_code:  pvz.code,
          packages:     JSON.stringify(this.packages),
        });
        this._tariff   = tariff;
        this._vue.tariff = tariff;
      } catch (err) {
        console.error('[SdekPvzWidget] tariff error:', err);
      }
    }

    // ----------------------------------------------------------
    // Видимые ПВЗ по bounding box карты
    // ----------------------------------------------------------
    async _updateVisiblePvz() {
      if (!this._map || !this._pvzAll.length) return;

      const [minLon, minLat, maxLon, maxLat] =
        this._map.getView().calculateExtent(this._map.getSize());

      const visible = this._pvzAll.filter(p => {
        const [la, lo] = p.location || [];
        if (!lo || !la) return false;
        return lo >= minLon && lo <= maxLon && la >= minLat && la <= maxLat;
      });

      // сортировка по расстоянию от центра
      const center = toLonLat(this._map.getView().getCenter());
      const sorted = [...visible].sort((a, b) => {
        const [la, lo] = a.location || [0, 0];
        const [lb, loB] = b.location || [0, 0];
        const da = Math.hypot(lo - center[0], la - center[1]);
        const db = Math.hypot(loB - center[0], lb - center[1]);
        return da - db;
      }).map(p => {
        const [la, lo] = p.location || [0, 0];
        const dist = Math.hypot(lo - center[0], la - center[1]) * 111;
        return { ...p, _dist: dist.toFixed(1) };
      });

      this._vue.list = sorted;
    }

    // ----------------------------------------------------------
    // Отрисовка маркеров
    // ----------------------------------------------------------
    _renderMarkers(pvzList) {
      if (!this._mapLayer) return;
      const src = this._mapLayer.getSource();
      src.clear();

      const { Feature, geom: { Point } } = window.ol;
      const { fromLonLat } = window.ol.proj;
      const { Style, Circle: Cls, Fill, Stroke, Text } = window.ol.style;

      pvzList.forEach(p => {
        const [la, lo] = p.location || [];
        if (!la || !lo) return;
        const f = new Feature({ geometry: new Point(fromLonLat([lo, la])) });
        f.setId(p.code);
        f.setStyle(new Style({
          image: new Cls({
            radius: 8,
            fill:   new Fill({ color: '#C69B3C' }),
            stroke: new Stroke({ color: '#fff', width: 2 }),
          }),
          text: new Text({
            text:      p.code,
            offsetY:   -14,
            font:      'bold 11px sans-serif',
            fill:      new Fill({ color: '#333' }),
          }),
        }));
        src.addFeature(f);
      });
    }

    // ----------------------------------------------------------
    // fetch-обёртка
    // ----------------------------------------------------------
    async _fetch(params) {
      const url = this.backendUrl + '?' + new URLSearchParams(params).toString();
      const res = await fetch(url);
      if (!res.ok) {
        const txt = await res.text().catch(() => '');
        throw new Error(`HTTP ${res.status}: ${txt}`);
      }
      const json = await res.json();
      if (json.error) throw new Error(json.error);
      return json;
    }

    // ----------------------------------------------------------
    // Утилиты
    // ----------------------------------------------------------
    _h(str) {
      return String(str ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }

    // ----------------------------------------------------------
    // CSS (изоляция — все классы с префиксом sdw-)
    // ----------------------------------------------------------
    _css() {
      return `
.sdw-overlay{
  position:fixed;inset:0;z-index:99998;
  background:rgba(0,0,0,.55);
  display:flex;align-items:center;justify-content:center;
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
}
.sdw-popup{
  background:#fff;border-radius:16px;
  width:92vw;max-width:1120px;height:82vh;max-height:740px;
  display:flex;flex-direction:column;overflow:hidden;
  box-shadow:0 24px 80px rgba(0,0,0,.25);
}
.sdw-popup__header{
  display:flex;align-items:center;justify-content:space-between;
  padding:16px 20px;border-bottom:1px solid #eee;flex-shrink:0;
}
.sdw-popup__title{font-size:17px;font-weight:700;color:#1a1a1a;}
.sdw-popup__close{
  background:none;border:none;font-size:30px;cursor:pointer;
  color:#aaa;line-height:1;padding:0 4px;
}
.sdw-popup__close:hover{color:#333;}
.sdw-popup__body{
  display:flex;flex:1;overflow:hidden;
}
.sdw-map-col{
  flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0;
}
.sdw-search-row{
  padding:10px 12px;background:#fff;flex-shrink:0;
  border-bottom:1px solid #f0f0f0;
}
.sdw-input{
  width:100%;padding:10px 14px;border:1.5px solid #e0e0e0;
  border-radius:8px;font-size:14px;box-sizing:border-box;
  transition:border-color .2s;
}
.sdw-input:focus{outline:none;border-color:#C69B3C;}
.sdw-error{color:#e53935;font-size:12px;margin-top:5px;}
.sdw-map{flex:1;width:100%;}
.sdw-sidebar{
  width:330px;flex-shrink:0;border-left:1px solid #eee;
  display:flex;flex-direction:column;overflow:hidden;background:#fafafa;
}
.sdw-sidebar__head{
  display:flex;align-items:center;justify-content:space-between;
  padding:12px 16px;font-weight:600;font-size:13px;color:#333;
  border-bottom:1px solid #eee;background:#fff;flex-shrink:0;
}
.sdw-badge{
  background:#C69B3C;color:#fff;border-radius:10px;
  padding:2px 9px;font-size:11px;font-weight:600;
}
.sdw-sidebar__err{
  padding:10px 16px;color:#e53935;font-size:12px;
  background:#fff3f3;border-bottom:1px solid #fdd;
}
.sdw-sidebar__list{
  flex:1;overflow-y:auto;padding:8px 10px;
}
.sdw-empty{text-align:center;color:#aaa;padding:30px 0;font-size:14px;}
.sdw-skeleton{
  height:76px;border-radius:8px;margin-bottom:6px;
  background:linear-gradient(90deg,#f0f0f0 25%,#e8e8e8 50%,#f0f0f0 75%);
  background-size:200% 100%;
  animation:sdw-shimmer 1.4s infinite;
}
@keyframes sdw-shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}
.sdw-pvz-item{
  background:#fff;border-radius:8px;padding:11px 13px;
  margin-bottom:5px;cursor:pointer;
  border:2px solid transparent;transition:border-color .15s,background .15s;
}
.sdw-pvz-item:hover{border-color:#e8d08a;}
.sdw-pvz-item--active{border-color:#C69B3C!important;background:#fdf8ee!important;}
.sdw-pvz-item__name{font-weight:600;font-size:13px;color:#222;margin-bottom:3px;}
.sdw-pvz-item__addr{font-size:12px;color:#666;line-height:1.4;}
.sdw-pvz-item__time{font-size:11px;color:#999;margin-top:3px;}
.sdw-pvz-item__dist{font-size:11px;color:#C69B3C;font-weight:600;margin-top:3px;}
.sdw-tariff{
  padding:14px 16px;background:#fff;
  border-top:1px solid #eee;flex-shrink:0;
}
.sdw-tariff__label{font-size:11px;color:#999;margin-bottom:4px;}
.sdw-tariff__price{font-size:24px;font-weight:800;color:#1a1a1a;}
.sdw-tariff__days{font-size:13px;color:#666;margin-top:3px;}
.sdw-sidebar__foot{
  padding:12px 16px;background:#fff;
  border-top:1px solid #eee;flex-shrink:0;
}
.sdw-btn{
  width:100%;padding:13px;border:none;border-radius:8px;
  background:#C69B3C;color:#fff;
  font-size:15px;font-weight:700;cursor:pointer;
  transition:background .2s;
}
.sdw-btn:hover:not(:disabled){background:#b8892f;}
.sdw-btn:disabled{background:#ddd;color:#aaa;cursor:not-allowed;}
      `;
    }
  }

  // экспорт
  global.SdekPvzWidget = SdekPvzWidget;

})(window);
