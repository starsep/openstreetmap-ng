import i18next from "i18next"
import * as L from "leaflet"
import { exportMapImage, getOptimalExportParams } from "./_image-export.js"
import { getLocationFilter } from "./_location-filter.js"
import { getMapBaseLayer, getMapEmbedHtml, getMapGeoUri, getMapShortUrl, getMapUrl } from "./_map-utils.js"
import { getSidebarToggleButton } from "./_sidebar-toggle-button.js"
import { getMarkerIcon } from "./_utils.js"

export const getShareSidebarToggleButton = () => {
    const control = getSidebarToggleButton("share", "javascripts.share.title")
    const controlOnAdd = control.onAdd

    control.onAdd = (map) => {
        const container = controlOnAdd(map)
        const sidebar = control.sidebar
        const button = control.button

        const markerCheckbox = sidebar.querySelector(".marker-checkbox")
        const linkRadioInput = sidebar.querySelector(".link-button")
        const linkInput = sidebar.querySelector(".link-input")
        const shortLinkRadioInput = sidebar.querySelector(".short-link-button")
        const shortLinkInput = sidebar.querySelector(".short-link-input")
        const embedRadioInput = sidebar.querySelector(".embed-button")
        const embedInput = sidebar.querySelector(".embed-input")
        const geoUriLink = sidebar.querySelector(".geo-uri-link")
        const exportForm = sidebar.querySelector(".export-form")
        const exportFormatSelect = exportForm.querySelector(".export-format-select")
        const customRegionCheckbox = exportForm.querySelector(".custom-region-checkbox")
        const offsetsWithDetailRadioInputs = exportForm
            .querySelectorAll(".detail-input")
            .map((input) => [parseInt(input.value), input])
        const exportButton = exportForm.querySelector("[type=submit]")

        // Null values until initialized
        let marker = null
        let locationFilter = null
        let optimalExportParams = null

        const updateLinks = () => {
            const showMarker = markerCheckbox.checked

            if (linkRadioInput.checked) {
                const link = getMapUrl(map, showMarker)
                linkInput.value = link
            } else if (shortLinkRadioInput.checked) {
                const shortLink = getMapShortUrl(map, showMarker)
                shortLinkInput.value = shortLink
            } else if (embedRadioInput.checked) {
                const markerLatLng = showMarker ? marker.getLatLng() : null
                const embed = getMapEmbedHtml(map, markerLatLng)
                embedInput.value = embed
            }
        }

        const updateGeoUri = () => {
            const geoUri = getMapGeoUri(map)
            geoUriLink.href = geoUri
            geoUriLink.textContent = geoUri
        }

        // On map move, update marker position if marker is enabled
        const onMapMove = () => {
            // Skip updates if the sidebar is hidden
            if (!button.classList.contains("active")) return
            if (markerCheckbox.checked) {
                marker.setLatLng(map.getCenter())
            }
        }

        // On map zoomend or moveend, update sidebar data
        const onMapZoomOrMoveEnd = () => {
            // Skip updates if the sidebar is hidden
            if (!button.classList.contains("active")) return

            updateLinks()
            updateGeoUri()
        }

        // On map zoomend or baselayerchange, update the optimal export params
        const onMapZoomOrLayerChange = () => {
            // Skip updates if the sidebar is hidden
            if (!button.classList.contains("active")) return

            const baseLayer = getMapBaseLayer(map)

            // Get the current base layer's min and max zoom
            const minZoom = baseLayer.options.minZoom
            const maxZoom = baseLayer.options.maxNativeZoom ?? baseLayer.options.maxZoom

            const bounds = customRegionCheckbox.checked ? locationFilter.getBounds() : map.getBounds()
            optimalExportParams = getOptimalExportParams(bounds)

            // Update the radio inputs availability
            for (const [zoomOffset, radioInput] of offsetsWithDetailRadioInputs) {
                const zoom = optimalExportParams.zoom + zoomOffset
                // TODO: Display the export resolution
                // const xResolution = Math.round(optimalExportParams.xResolution * 2 ** zoomOffset)
                // const yResolution = Math.round(optimalExportParams.yResolution * 2 ** zoomOffset)
                const isAvailable = minZoom <= zoom && zoom <= maxZoom

                radioInput.disabled = !isAvailable

                if (radioInput.checked && !isAvailable) {
                    radioInput.checked = false
                    radioInput.dispatchEvent(new Event("change"))
                }
            }
        }

        // On marker checkbox change, display/hide the marker
        const onMarkerCheckboxChange = () => {
            if (markerCheckbox.checked) {
                if (!marker) {
                    marker = L.marker(map.getCenter(), {
                        icon: getMarkerIcon("blue", true),
                        draggable: true,
                        autoPan: true,
                    })
                    marker.addEventListener("dragend", onMarkerDragEnd)
                } else {
                    marker.setLatLng(map.getCenter())
                }

                // Display marker and chance zoom mode to center
                map.addLayer(marker)
                map.options.scrollWheelZoom = map.options.doubleClickZoom = "center"
            } else {
                // Hide marker and reset zoom mode
                map.removeLayer(marker)
                map.options.scrollWheelZoom = map.options.doubleClickZoom = true
            }
        }

        const onExportFormSubmit = async (e) => {
            e.preventDefault()

            if (exportButton.disabled) return

            const originalInner = exportButton.innerHTML
            exportButton.disabled = true
            exportButton.textContent = i18next.t("javascripts.share.exporting")

            try {
                // Get export params from the form
                const mimeType = exportFormatSelect.value
                const fileExtension = exportFormatSelect.selectedOptions[0].dataset.fileExtension
                const bounds = customRegionCheckbox.checked ? locationFilter.getBounds() : map.getBounds()
                const zoomOffset = parseInt(exportForm.querySelector(".detail-input:checked").value)
                const zoom = optimalExportParams.zoom + zoomOffset
                const baseLayer = getMapBaseLayer(map)

                // Create image blob and download it
                const blob = await exportMapImage(mimeType, bounds, zoom, baseLayer)

                const now = new Date()
                const date = `${now.toISOString().slice(0, 10)} ${now.toLocaleTimeString().replace(/:/g, "-")}`

                const a = document.createElement("a")
                a.href = URL.createObjectURL(blob)
                a.download = `Map ${date}.${fileExtension}`
                a.click()
            } finally {
                exportButton.innerHTML = originalInner
                exportButton.disabled = false
            }
        }

        // On custom region checkbox change, enable/disable the location filter
        const onCustomRegionCheckboxChange = () => {
            if (customRegionCheckbox.checked) {
                if (!locationFilter) {
                    locationFilter = getLocationFilter({
                        enableButton: false,
                        adjustButton: false,
                    })
                    locationFilter.addEventListener("change", onMapZoomOrLayerChange)
                }

                // By default, location filter is slightly smaller than the current view
                locationFilter.setBounds(map.getBounds().pad(-0.2))

                map.addLayer(locationFilter)
            } else {
                map.removeLayer(locationFilter)
            }

            onMapZoomOrLayerChange()
        }

        // On marker drag end, center map to marker
        const onMarkerDragEnd = () => {
            map.removeEventListener("move", onMapMove)
            map.panTo(marker.getLatLng())
            map.addOneTimeEventListener("moveend", () => {
                map.addEventListener("move", onMapMove)
            })
        }

        const onButtonClick = () => {
            if (button.classList.contains("active")) {
                // On sidebar shown, force update
                onMapZoomOrMoveEnd()
                onMapZoomOrLayerChange()
            } else {
                // On sidebar hidden, deselect the marker checkbox
                if (markerCheckbox.checked) {
                    markerCheckbox.checked = false
                    markerCheckbox.dispatchEvent(new Event("change"))
                }

                // On sidebar hidden, deselect the custom region checkbox
                if (customRegionCheckbox.checked) {
                    customRegionCheckbox.checked = false
                    customRegionCheckbox.dispatchEvent(new Event("change"))
                }
            }
        }

        // Listen for events
        map.addEventListener("move", onMapMove)
        map.addEventListener("zoomend moveend", onMapZoomOrMoveEnd)
        map.addEventListener("zoomend baselayerchange", onMapZoomOrLayerChange)
        button.addEventListener("click", onButtonClick)
        markerCheckbox.addEventListener("change", onMarkerCheckboxChange)
        linkRadioInput.addEventListener("change", () => {
            if (linkRadioInput.checked) updateLinks()
        })
        shortLinkRadioInput.addEventListener("change", () => {
            if (shortLinkRadioInput.checked) updateLinks()
        })
        embedRadioInput.addEventListener("change", () => {
            if (embedRadioInput.checked) updateLinks()
        })
        exportForm.addEventListener("submit", onExportFormSubmit)
        customRegionCheckbox.addEventListener("change", onCustomRegionCheckboxChange)

        return container
    }

    return control
}
