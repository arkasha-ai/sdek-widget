/**
 * index.js — entry point
 * export: SdekPvzWidget class + Vue components
 */
import { SdekPvzWidget } from './SdekPvzWidget.js';
import PvzList from './components/PvzList.vue';
import PvzDetail from './components/PvzDetail.vue';
import DoorPanel from './components/DoorPanel.vue';
import MapPane from './components/MapPane.vue';
import SegmentedControl from './components/SegmentedControl.vue';

export { SdekPvzWidget, PvzList, PvzDetail, DoorPanel, MapPane, SegmentedControl };

// Глобальный экспорт для UMD <script>-тега: window.SdekPvzWidget = class
if (typeof window !== 'undefined' && !window.__sdekPvzWidgetExported) {
  window.__sdekPvzWidgetExported = true;
  window.SdekPvzWidget = SdekPvzWidget;
}
