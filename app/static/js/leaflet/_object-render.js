import * as L from "leaflet"
import "../_types.js"
import { getMarkerIcon } from "./_utils.js"

/**
 * Add objects to the feature group layer
 * @param {L.LayerGroup} layerGroup Layer group
 * @param {OSMObject[]} objects Array of objects
 * @param {object} styles Styles
 * @param {object} styles.changeset Changeset style
 * @param {object} styles.element Element style
 * @param {object} styles.noteHalo Note halo style
 * @param {boolean} renderAreas Whether to render areas
 * @returns {L.Layer[]} Array of added layers
 */
export const renderObjects = (layerGroup, objects, styles, renderAreas = true) => {
    const layers = []
    const markers = []

    /**
     * @param {OSMChangeset} changeset
     */
    const processChangeset = (changeset) => {
        for (const [minLon, minLat, maxLon, maxLat] of changeset.bounds ?? []) {
            const latLngBounds = L.latLngBounds(L.latLng(minLat, minLon), L.latLng(maxLat, maxLon))
            const layer = L.rectangle(latLngBounds, styles.changeset)
            layer.object = changeset
            layers.push(layer)
        }
    }

    /**
     * @param {OSMNote} note
     */
    const processNote = (note) => {
        const interactive = note.interactive !== undefined ? Boolean(note.interactive) : true
        const draggable = note.draggable !== undefined ? Boolean(note.draggable) : false
        const latLng = L.latLng(note.lat, note.lon)
        const layer = L.circleMarker(latLng, styles.noteHalo)
        const marker = L.marker(latLng, {
            ...styles.note,
            icon: getMarkerIcon(note.icon, false),
            keyboard: interactive,
            interactive: interactive,
            draggable: draggable,
            autoPan: draggable,
        })
        layer.object = note
        layer.marker = marker
        layers.push(layer)
        markers.push(marker)
    }

    /**
     * @param {OSMNode} node
     */
    const processNode = (node) => {
        const layer = L.circleMarker(node.geom, styles.element)
        layer.object = node
        layers.push(layer)
    }

    /**
     * @param {OSMWay} way
     */
    const processWay = (way) => {
        let geom = way.geom
        let layer
        if (renderAreas && way.area) {
            geom = geom.slice(0, -1) // remove last == first
            layer = L.polygon(geom, styles.element)
        } else {
            layer = L.polyline(geom, styles.element)
        }
        layer.object = way
        layers.push(layer)
    }

    const processMap = {
        changeset: processChangeset,
        note: processNote,
        node: processNode,
        way: processWay,
    }

    for (const object of objects) {
        const fn = processMap[object.type]
        if (fn) fn(object)
        else console.error("Unsupported feature type", object)
    }

    // Render icons on top of the feature layers
    if (layers.length) {
        console.debug("Render", layers.length, "objects")
        layerGroup.addLayer(L.layerGroup(layers))
    }
    if (markers.length) {
        console.debug("Render", markers.length, "markers")
        layerGroup.addLayer(L.layerGroup(markers))
    }

    return layers
}
