import { Map, TileLayer, DivIcon, GeoJSON as GeoJsonLayer, Marker, PointExpression, PathOptions, LatLng, Control, control as lControls, Layer, Icon } from "leaflet";
import 'leaflet/dist/leaflet.css'
import { GeoJsonObject, Feature, GeometryCollection, Geometry, FeatureCollection, MultiPolygon, MultiPoint } from 'geojson';
import Swal from 'sweetalert2'
import 'sweetalert2/dist/sweetalert2.min.css'
import 'animate.css';
import { create, map, memoize } from 'lodash';

interface Transport {
  listen: (msgType: string, callback: (data: any) => void) => void;
  emit: (msgType: string, data?: any) => void;
}

async function createTauriTransport(): Promise<Transport> {
  const tauri = (await import('@tauri-apps/api/event')).default
  return {
    listen: (msgType, callback) => {
      tauri.listen(msgType, event => {
        callback(event.payload)
      })
    },
    emit: (msgType, data) => {
      tauri.emit(msgType, data)
    }
  }
}

async function createWsTransport(): Promise<Transport> {
  const socket = new WebSocket('ws://localhost:8000');
  const errorPromise = new Promise<void>((_, reject) => {
    socket.addEventListener('error', () => reject('WebSocket error'));
  })
  const openPromise = new Promise<void>((resolve, _) => {
    socket.addEventListener('open', () => resolve());
  });
  await Promise.race([openPromise, errorPromise]);
  const listeners: { type: string, callback: (data: any) => void }[] = [];
  socket.addEventListener('message', function (event) {
    const msg = JSON.parse(event.data);
    console.log(`Received message:`, msg.type, msg.data);
    const msgListeners = listeners.filter(listener => listener.type === msg.type);
    if (msgListeners.length === 0) {
      throw new Error(`No listeners for message type ${msg.type}`);
    }
    for (const listener of msgListeners) {
      listener.callback(msg.data);
    }
  });
  return {
    listen: (type, callback) => {
      listeners.push({ type, callback });
    },
    emit: (type, data) => {
      console.log(`Sending message:`, type, data);
      socket.send(JSON.stringify({
        type,
        data: data ?? null
      }));
    }
  }
}

function createMap(initLocation: LatLng) {
  const map = new Map('map')
  console.log(map)
  map.setView(initLocation, 14);

  const osm = new TileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
  });
  map.addLayer(osm);

  return map;
}

const colors = ['#004d61', '#5bd1d7', '#FFBA49', '#C2E812', "#6E4555", "#504136", "#21712B", "#51FD68"];

// 9.9999 => 99.99 => 99.0 => 9.9
function toFixedFlooredTenths(number: number) {
  return (Math.floor(number * 10) / 10).toFixed(1)
}

const createMarkerIcon = (
  color: string, nbroOverlaps: number, overlapNbr: number
) => {
  const sliceAngle = Math.PI * 2 / nbroOverlaps
  const startAngle = sliceAngle * overlapNbr;
  const endAngle = startAngle + sliceAngle;
  const radius = 10;
  const arcStart: PointExpression = [
    10 + Math.sin(startAngle) * radius,
    10 + Math.cos(startAngle) * radius
  ];
  const arcEnd: PointExpression = [
    10 + Math.sin(endAngle) * radius,
    10 + Math.cos(endAngle) * radius
  ];
  return new DivIcon({
    html: `
        <svg data-nbro-overlaps="${nbroOverlaps}" data-overlap-nbr="${overlapNbr}" width="20" height="20" xmlns="http://www.w3.org/2000/svg" version="1.1" preserveAspectRatio="none">
            <path fill="${color}" d="
              M 10 10
              L ${toFixedFlooredTenths(arcStart[0])} ${toFixedFlooredTenths(arcStart[1])}
              A 10 10 0 1 0 ${toFixedFlooredTenths(arcEnd[0])} ${toFixedFlooredTenths(arcEnd[1])}
              L 10 10
              Z"/>
        </svg>
    `,
    className: "",
    iconSize: [20, 20],
    iconAnchor: [10, 10]
  })
};

// Ugly hack to be able to display the index of the geometries in a collection
// as a tooltip in leaflet.
function addGeometryCollectionFeatureIndices(geometry: GeoJsonObject) {
  if (geometry.type === 'Feature') {
    const feature = geometry as Feature
    if (feature.geometry.type === 'GeometryCollection') {
      const collection = feature.geometry as GeometryCollection
      collection.geometries.map((geometry, geometry_index) => {
        const properties = feature.properties as any
        (geometry as any).index = `${properties.name}: ${geometry_index}`
      })
    }
  }
}

function createTitle(latLng: LatLng, geometryIndices: string[]) {
  return `${latLng.lat.toFixed(2)}, ${latLng.lng.toFixed(2)}: ${geometryIndices.join(', ')}`
}

function createGeoJsonLayer(map: Map, geometry: GeoJsonObject, color: string, lineStringThickness = 8) {
  addGeometryCollectionFeatureIndices(geometry)
  return new GeoJsonLayer(
    geometry,
    {
      style: feature => {
        const options: PathOptions = {
          color,
          fillColor: color,
        }
        const makeThickIfLineString = (geometry: Geometry) => {
          if (geometry.type === 'LineString') {
            options.weight = lineStringThickness;
          }
        }
        if (feature?.geometry !== undefined) makeThickIfLineString(feature?.geometry);
        if (feature?.geometry.type === 'GeometryCollection') {
          const collection = feature.geometry as GeometryCollection
          for (const geometry of collection.geometries) {
            makeThickIfLineString(geometry);
          }
        }
        return options
      },
      onEachFeature: (feature, layer) => {
        layer.bindTooltip(feature.properties.name);
      },
      pointToLayer: function(_geoJsonPoint, latLng) {
        const existingMarkers: Marker[] = [];
        map.eachLayer(layer => {
          if (layer instanceof Marker && layer.getLatLng().equals(latLng)) {
            existingMarkers.push(layer);
          }
        });
        const nbroOverlaps = existingMarkers.length + 1;
        const geometryIndex = (_geoJsonPoint.geometry as any).index
        existingMarkers.forEach((existingMarker, overlapNbr) => {
          const existingMarkerColor: string = (existingMarker as any)._color;
          const geometryIndices: string[] = (existingMarker as any)._geometryIndices;
          geometryIndices.push(geometryIndex);
          existingMarker.setIcon(createMarkerIcon(
            existingMarkerColor, nbroOverlaps, overlapNbr
          ));
          existingMarker.options.title = createTitle(latLng, geometryIndices)
        });
        const icon = createMarkerIcon(
          color, nbroOverlaps, nbroOverlaps - 1
        );
        const geometryIndices = [geometryIndex];
        const marker = new Marker(latLng, {
          icon,
          title: createTitle(latLng, geometryIndices),
        });
        (marker as any)._color = color;
        (marker as any)._geometryIndices = geometryIndices;
        return marker;
      }
    }
  )
}

function addGeometries(map: Map, geometries: GeoJsonObject[]) {
  console.log('Adding new geometries')
  if (geometries.length > colors.length) console.error('Too many geometries/too few colors');
  console.log(geometries)
  geometries.forEach((geometry, i) => {
    const layerColor = colors[i];
    createGeoJsonLayer(map, geometry, layerColor);
  });
}

interface ShortestPath {
  distance: number;
  path: Feature;
}

const Toast = Swal.mixin({
  toast: true,
  position: 'top-end',
  showConfirmButton: false,
  timer: 4000,
  timerProgressBar: true,
  showCloseButton: true,
  showClass: {
    popup: 'animate__animated animate__fadeInDown'
  },
  hideClass: {
    popup: 'animate__animated animate__fadeOutUp'
  },
  didOpen: (toast) => {
    toast.addEventListener('mouseenter', Swal.stopTimer)
    toast.addEventListener('mouseleave', Swal.resumeTimer)
  }
})

function createControlPanel(
  startPointMarker: Marker,
  endPointMarker: Marker,
  map: Map,
  transport: Transport
) {
  const createButton = (text: string, onClick: () => void) => {
    const button = document.createElement('button');
    Object.assign(button.style, {
      marginBottom: '0.5rem',
      color: '#fff',
      border: '0.1rem solid #fff',
      backgroundColor: 'transparent',
    } as CSSStyleDeclaration);
    button.innerText = text;
    button.onclick = onClick;
    return button;
  };

  const createOptionSpinner = (label: string, options: string[], onChange: (value: string) => void) => {
    const container = document.createElement('div');

    const labelElement = document.createElement('label');
    Object.assign(labelElement.style, {
      display: 'flex',
      flexDirection: 'column',
      color: '#fff',
      margin: '0px',
    } as CSSStyleDeclaration);
    labelElement.innerText = label;
    container.appendChild(labelElement);

    const spinner = document.createElement('select');
    Object.assign(spinner.style, {
      marginBottom: '0.5rem',
      color: '#fff',
      border: '0.1rem solid #fff',
      backgroundColor: 'transparent',
    } as CSSStyleDeclaration);
    for (const option of options) {
      const optionElement = document.createElement('option');
      optionElement.innerText = option;
      spinner.appendChild(optionElement);
    }
    spinner.addEventListener('input', () => {
      onChange(spinner.value);
    });
    container.appendChild(spinner);

    return container;
  };

  const createSlider = (text: string, max: number, onChange: (value: number) => void) => {
    const container = document.createElement('div');

    const valueSpan = document.createElement('span');
    valueSpan.innerText = '0';
    Object.assign(valueSpan.style, {
      color: '#fff',
    } as CSSStyleDeclaration);
    container.appendChild(valueSpan);

    const label = document.createElement('label');
    Object.assign(label.style, {
      display: 'flex',
      flexDirection: 'column',
      color: '#fff',
      margin: '0px',
    } as CSSStyleDeclaration);
    label.innerText =  text;
    container.appendChild(label);

    const input = document.createElement('input');
    Object.assign(input.style, {
      marginBottom: '0px',
    });
    input.type = 'range';
    input.min = '0';
    const sliderMax = 10000;
    input.max = sliderMax.toString();
    input.step = '1';
    input.value = '0';
    input.addEventListener('input', () => {
      const value = (input.valueAsNumber / sliderMax) * max;
      valueSpan.innerText = `${value.toFixed(2)}`;
      onChange(value);
    });
    label.appendChild(input);
    
    return container;
  };

  // class ButtonControl extends Control {
  //   label: string;
  //   onClick: () => void;
  
  //   constructor(label: string, onClick: () => void) {
  //     super();
  //     this.label = label;
  //     this.onClick = onClick;
  //   }
  
  //   onAdd?(_map: Map): HTMLElement {
  //     const container = document.createElement('div');
  //     Object.assign(container.style, {
  //       display: 'flex',
  //       flexDirection: 'column',
  //     } as CSSStyleDeclaration);
  //     const button = document.createElement('button');
  //     button.innerText = this.label;
  //     button.addEventListener('click', this.onClick);
  //     button.style.marginBottom = '1em';
  //     container.appendChild(button);
  //     return container;
  //   }
  //   onRemove?(_map: Map): void {};
  // }
  let maxDistanceInitially = 600;
  let maxDistanceAfterCharge = 1000;
  let visibilityOptimizationMode = 'Naive';

  const controlPanel = document.createElement('div');
  Object.assign(controlPanel.style, {
    position: 'absolute',
    zIndex: 1000,
    bottom: 0,
    display: 'flex',
    flexDirection: 'column',
    padding: '0.5em',
    backgroundColor: 'hsla(0, 0%, 0%, 0.4)',
  } as unknown as CSSStyleDeclaration);

  controlPanel.replaceChildren(
    createOptionSpinner('Visibility optimization mode', ['Naive', 'Sweep', 'OptimizedSweep'], value => {
      visibilityOptimizationMode = value;
    }),
    createButton('Load graph', () => {
      Toast.fire({
        title: 'Loading nav graph...',
        icon: 'info',
      });
      transport.emit('visibility-graph', {
        visibilityOptimizationMode
      });
    }),
    createButton('Load waters', () => {
      transport.emit('load-waters', null);
    }),
    createButton('Load restricted airspace', () => {
      transport.emit('load-restricted-airspace', null);
    }),
    createButton('Calc direct path', () => {
      const startCoord = startPointMarker.getLatLng();
      const endCoord = endPointMarker.getLatLng();
      transport.emit('calc-path', {
        start: startCoord,
        end: endCoord,
        visibilityOptimizationMode,
      });
    }),
    createSlider('Max distance initially', 10000, (value) => {
      maxDistanceInitially = value;
    }),
    createSlider('Max distance after charge', 10000, (value) => {
      maxDistanceAfterCharge = value;
    }),
    createButton('Plan path', () => {
      const startCoord = startPointMarker.getLatLng();
      const endCoord = endPointMarker.getLatLng();
      transport.emit('plan', {
        start: startCoord,
        end: endCoord,
        maxDistanceInitially,
        maxDistanceAfterCharge,
        visibilityOptimizationMode
      });
    }),
    createButton('Clear debug', () => {
      map.eachLayer(layer => {
        if ((layer as any).isDebug) {
          map.removeLayer(layer);
        }
      })
    }),
  );
  return controlPanel;
}

function createResourceMarkerIcon(path: string) {
  return new Icon({
    iconUrl: path,
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowUrl: 'node_modules/leaflet/dist/images/marker-shadow.png',
    tooltipAnchor: [16, -28],
    shadowSize: [41, 41],
  });
}

async function init() {
  const initLocation = new LatLng(50.98, 4.52);
  const transport = await createWsTransport();
  const startIcon = createResourceMarkerIcon('res/start-marker.svg');
  const endIcon = createResourceMarkerIcon('res/end-marker.svg');
  const startPointMarker = new Marker(initLocation, { draggable: true, icon: startIcon });
  const endPointMarker = new Marker(initLocation, { draggable: true, icon: endIcon });
  const map = createMap(initLocation);
  const controlPanel = createControlPanel(
    startPointMarker,
    endPointMarker,
    map,
    transport
  );
  document.body.appendChild(controlPanel);
  map.addLayer(startPointMarker);
  map.addLayer(endPointMarker);
  const layersControl = lControls.layers().addTo(map);

  transport.emit('map-ready');
  let navGraphLayer: GeoJsonLayer | null = null;
  let shortestPathLayer: GeoJsonLayer | null = null;
  transport.listen('obstacles', (obstacles: Feature<MultiPolygon>) => {
    createGeoJsonLayer(map, obstacles, '#ff502f').addTo(map);
  });
  transport.listen('waters', data => {
    const waters: Feature<MultiPolygon> = data;
    // const waters: Feature<MultiPolygon> = data.waters;
    // const pois: Feature<MultiPoint> = data.pois;
    createGeoJsonLayer(map, waters, "#495d69").addTo(map);
    // createGeoJsonLayer(map, pois, "#ff5d69").addTo(map);
  });
  transport.listen('restricted-airspace', data => {
    const restricted_airspace: Feature<MultiPolygon> = data;
    createGeoJsonLayer(map, restricted_airspace, "#845a9e").addTo(map);
  });
  transport.listen('nav-graph', (data: {
    graph: FeatureCollection,
    duration: number,
  }) => {
    const { graph, duration } = data;
    if (navGraphLayer !== null) {
      map.removeLayer(navGraphLayer);
      layersControl.removeLayer(navGraphLayer);
    }
    navGraphLayer = createGeoJsonLayer(map, graph, colors[1], 3);
    // navGraphLayer.addTo(map);
    layersControl.addOverlay(navGraphLayer, 'Nav graph');
    Toast.fire({
      title: `Nav graph loaded. Took ${(duration/1000).toFixed(1)}s.`,
      icon: 'info',
    });
  });
  transport.listen('debug-geometries', (debugGeometries: FeatureCollection) => {
    const existingDebugLayers: Layer[] = [];
    map.eachLayer(layer => {
      if ((layer as any).isDebug) {
        existingDebugLayers.push(layer);
      }
    });
    const color = colors[existingDebugLayers.length % colors.length];
    const layer = createGeoJsonLayer(map, debugGeometries, color);
    (layer as any).isDebug = true;
    layer.addTo(map);
  });
  transport.listen('shortest-path-calculated', (shortestPath: ShortestPath | null) => {
    if (shortestPath == null) {
      Toast.fire({
        title: 'No path found',
        icon: 'warning',
      });
    } else {
      if (shortestPathLayer !== null) {
        map.removeLayer(shortestPathLayer);
        layersControl.removeLayer(shortestPathLayer);
      }
      shortestPathLayer = createGeoJsonLayer(map, shortestPath.path, '#b900e3').addTo(map);
      shortestPathLayer.addTo(map);
      layersControl.addOverlay(shortestPathLayer, 'Shortest path');
    }
  });
  transport.listen('planner-path-calculated', (legs: Feature[][]) => {
    console.info('planner-path-calculated', legs);
    const existingDebugLayers: Layer[] = [];
    map.eachLayer(layer => {
      if ((layer as any).isDebug) {
        existingDebugLayers.push(layer);
      }
    });
    Toast.fire({
      title: `${legs.length} legs`,
      icon: 'info',
    });
    legs.forEach((leg, legIndex) => {
      const color = colors[(existingDebugLayers.length + legIndex) % colors.length];
      const [lastReachablePoint, path] = leg;
      const lastReachablePointLayer = createGeoJsonLayer(map, lastReachablePoint, color);
      (lastReachablePointLayer as any).isDebug = true;
      lastReachablePointLayer.addTo(map);
      const pathLayer = createGeoJsonLayer(map, path, color);
      (pathLayer as any).isDebug = true;
      pathLayer.addTo(map);
    });
  });
  transport.listen('error', (error: string) => {
    const msg = `Server error: ${error}`;
    console.error(msg);
    Toast.fire({
      title: msg,
      icon: 'error',
    });
  });
}

init().then(() => {
  console.log('init done');
}, (err) => {
  console.error(err);
  const errSpan = document.createElement('span');
  errSpan.innerText = err;
  Object.assign(errSpan.style, {
    color: 'darkred',
    fontWeight: 'bold',
    fontSize: '1.5rem',
  } as CSSStyleDeclaration);
  document.body.prepend(errSpan);
});
